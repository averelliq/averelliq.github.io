"""Run the Shorts generator with retries limited to transient Gemini API requests.

Never retry the entire pipeline: doing so could upload duplicate YouTube videos.
"""
from __future__ import annotations

import os
import random
import re
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import requests

import main as bot

_ORIGINAL_POST = requests.post
_TRANSIENT_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 5
_DEFAULT_FALLBACK_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
)


def _retry_delay(response: requests.Response | None, attempt: int) -> float:
    backoff = min(30.0, 2.0 ** (attempt + 1)) + random.uniform(0, 1)
    if response is None:
        return backoff
    header = response.headers.get("Retry-After", "").strip()
    if header:
        try:
            return min(60.0, max(0.0, float(header)))
        except ValueError:
            try:
                deadline = parsedate_to_datetime(header)
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                return min(60.0, max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                pass
    return backoff


def _model_candidates(url: str) -> list[tuple[str, str]]:
    match = re.search(r"/models/([^/:]+):generateContent", url)
    if not match:
        return [("", url)]
    primary = match.group(1)
    configured = [
        item.strip() for item in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",")
        if item.strip()
    ]
    models = [primary, *configured, *_DEFAULT_FALLBACK_MODELS]
    unique: list[str] = []
    for model in models:
        if model not in unique:
            unique.append(model)
    return [(model, url.replace(f"/models/{primary}:", f"/models/{model}:")) for model in unique]


def resilient_post(url: str, *args, **kwargs):
    if "generativelanguage.googleapis.com" not in url:
        return _ORIGINAL_POST(url, *args, **kwargs)

    candidates = _model_candidates(url)
    last_response = None
    last_exception: Exception | None = None

    for model_index, (model, model_url) in enumerate(candidates, start=1):
        if model:
            print(f"Gemini model attempt {model_index}/{len(candidates)}: {model}", flush=True)
        for attempt in range(_MAX_ATTEMPTS):
            response = None
            try:
                response = _ORIGINAL_POST(model_url, *args, **kwargs)
                last_response = response
                if response.status_code not in _TRANSIENT_STATUS:
                    if model and model_index > 1:
                        print(f"Gemini fallback succeeded with {model} (HTTP {response.status_code}).", flush=True)
                    return response
                reason = f"HTTP {response.status_code}"
                if attempt == _MAX_ATTEMPTS - 1:
                    print(
                        f"Gemini {model or 'primary'} temporary {reason} persisted after {_MAX_ATTEMPTS} attempts; trying fallback model.",
                        flush=True,
                    )
                    break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_exception = exc
                reason = type(exc).__name__
                if attempt == _MAX_ATTEMPTS - 1:
                    print(
                        f"Gemini {model or 'primary'} {reason} persisted after {_MAX_ATTEMPTS} attempts; trying fallback model.",
                        flush=True,
                    )
                    break
            wait = _retry_delay(response, attempt)
            print(
                f"Gemini transient error ({reason}); attempt {attempt + 1}/{_MAX_ATTEMPTS}, retrying in {wait:.1f}s.",
                flush=True,
            )
            time.sleep(wait)

    if last_response is not None:
        return last_response
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Gemini request failed before receiving a response")


def run() -> None:
    bot.requests.post = resilient_post
    if os.getenv("SHORTS_SKIP_UPLOAD") == "1":
        def skip_upload(video_path, plan):
            print("SMOKE TEST: YouTube upload intentionally disabled; video remains an artifact.", flush=True)
            return None
        bot.upload_youtube = skip_upload
    bot.main()


if __name__ == "__main__":
    run()

"""Retry ONLY transient outages in mandatory Gemini visual review.

A retry never converts a negative or inconclusive model decision into approval.
If the service stays unavailable, the video is NOT uploaded.
"""
from __future__ import annotations

import time

import requests
import visual_guard

_installed = False


def install() -> None:
    global _installed
    if _installed:
        return
    previous = visual_guard._model_review

    def review_with_transient_retry(plan, previews):
        attempts = 5
        for attempt in range(attempts):
            try:
                return previous(plan, previews)
            except requests.HTTPError as exc:
                response = exc.response
                status = response.status_code if response is not None else None
                if status not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                    raise
                # Concurrent calls can exhaust a short model burst quota. Back off
                # progressively, never bypass the review or reinterpret a rejection.
                delay = (15, 30, 45, 60)[attempt] if status == 429 else (6, 12, 20, 30)[attempt]
                print(f"Visual review temporarily unavailable (HTTP {status}); retry {attempt + 1}/{attempts - 1} in {delay}s; upload remains blocked", flush=True)
                time.sleep(delay)
        raise AssertionError("unreachable")

    visual_guard._model_review = review_with_transient_retry
    _installed = True

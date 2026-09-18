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
        for attempt in range(3):
            try:
                return previous(plan, previews)
            except requests.HTTPError as exc:
                response = exc.response
                status = response.status_code if response is not None else None
                if status not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                delay = 6 * (attempt + 1)
                print(f"Visual review temporarily unavailable (HTTP {status}); retry {attempt + 1}/2 in {delay}s; upload remains blocked", flush=True)
                time.sleep(delay)
        raise AssertionError("unreachable")

    visual_guard._model_review = review_with_transient_retry
    _installed = True

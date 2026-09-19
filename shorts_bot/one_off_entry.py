"""Run one explicitly requested Short with a fixed, independently selected topic.

This entrypoint only runs from the dedicated GitHub push workflow. It reuses
all existing editorial, footage, render, duplicate, and upload quality gates.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import montage_entry
import trend_ideas

REQUEST = Path(__file__).with_name("one_off_request.json")


def main() -> None:
    if os.getenv("GITHUB_EVENT_NAME") != "push" or os.getenv("SHORTS_ONE_OFF_PUBLISH") != "1":
        raise RuntimeError("One-off publication requires its dedicated push workflow")
    if os.getenv("SHORTS_SKIP_UPLOAD") == "1":
        raise RuntimeError("One-off publication cannot silently become a smoke test")
    if os.getenv("GITHUB_REPOSITORY") != "averelliq/averelliq.github.io":
        raise RuntimeError("Unexpected GitHub repository")
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    if not isinstance(request, dict) or set(request) != {"request_id", "theme", "topic"}:
        raise ValueError("Expected a one-off request with request_id, theme, and topic only")
    if request["request_id"] != "curiorush-candle-2026-09-20":
        raise ValueError("Unexpected one-off request identifier")
    if request["theme"] != "everyday":
        raise ValueError("Unexpected one-off theme")
    topic = request["topic"]
    if topic != "why a candle flame flickers" or not re.fullmatch(r"[a-z ]{8,90}", topic):
        raise ValueError("Unexpected one-off topic")

    # us_trends.install normally replaces the topic picker. Install it first,
    # then pin only this run's subject so both plan creation and validation
    # agree. This does not alter the code used by scheduled publications.
    original_install = montage_entry.us_trends.install

    def install_and_pin() -> None:
        original_install()
        trend_ideas._CACHE["everyday"] = topic
        trend_ideas._REFERENCES.pop("everyday", None)
        trend_ideas.pick_topic = lambda theme, fallback, model_json: topic

    montage_entry.us_trends.install = install_and_pin
    print(f"ONE-OFF ORIGINAL SHORT: {topic}", flush=True)
    montage_entry.main()


if __name__ == "__main__":
    main()

"""One-off film-first Short about how an industrial steel gear is made.

The existing authenticity, originality, audio, and final-render gates must pass
before the regular uploader can publish. Do not substitute another subject.
The 2026-09-20 retry uses quota-aware Gemini routing and batched footage review.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import footage_first
import montage_entry
import process_formats
import trend_ideas
import upgrade

REQUEST = Path(__file__).with_name("gear_short_request.json")
TOPIC = "how a steel gear is made"
REQUEST_ID = "curiorush-steel-gear-making-2026-09-20"


def main() -> None:
    if os.getenv("GITHUB_EVENT_NAME") != "push" or os.getenv("SHORTS_GEAR_ONE_OFF") != "1":
        raise RuntimeError("Gear Short requires its dedicated GitHub push workflow")
    if os.getenv("GITHUB_REPOSITORY") != "averelliq/averelliq.github.io":
        raise RuntimeError("Unexpected repository; refusing YouTube upload")
    if os.getenv("SHORTS_SKIP_UPLOAD") == "1":
        raise RuntimeError("Publish request must not silently become a preview")
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    if not isinstance(request, dict) or set(request) != {"request_id", "theme", "topic"}:
        raise ValueError("Invalid gear request structure")
    if request != {"request_id": REQUEST_ID, "theme": "history", "topic": TOPIC}:
        raise ValueError("Unexpected gear Short request; refusing to change topic")

    original_install = montage_entry.process_formats.install

    def install_and_pin() -> None:
        original_install()
        if TOPIC not in upgrade.TOPICS["history"] or TOPIC not in footage_first.SPECIAL:
            raise RuntimeError("Dedicated gear footage search is not installed")
        trend_ideas._CACHE["history"] = TOPIC
        trend_ideas._REFERENCES.pop("history", None)
        footage_first._seed = lambda theme: TOPIC
        upgrade.choose_topic = lambda theme: TOPIC
        print("GEAR ONE-OFF: topic pinned to genuine industrial steel gear manufacturing", flush=True)

    montage_entry.process_formats.install = install_and_pin
    print("GEAR SHORT: footage first -> original English script -> CTA -> quality checks -> public upload", flush=True)
    montage_entry.main()


if __name__ == "__main__":
    main()

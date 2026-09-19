"""One requested Short: pin the topic and insist on relevant candle-only footage.

All scheduled Shorts and every editorial, stock and final QC gate stay intact.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import editorial_upgrade
import montage_entry
import quality_entry
import trend_ideas

REQUEST = Path(__file__).with_name("one_off_request.json")
CANDLE_QUERIES = (
    "candle flame flickering closeup",
    "single candle flame dark",
    "lit candle flame flickering",
    "candle wick burning flame",
    "candle flame slow motion",
    "small candle burning closeup",
    "yellow candle flame closeup",
    "candle flame moving closeup",
)
CANDLE_BACKUPS = (
    "candle flame flickering",
    "burning candle close up",
    "candle wick flame",
    "single candle burning",
)


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

    # Observations of the visible flame explain the airflow. Never illustrate
    # the word 'hot air' with balloons or landscape footage.
    editorial_upgrade.POLICY += (
        "\nONE-OFF CANDLE VISUAL BRIEF: Every scene shows a real, visibly burning "
        "candle or its visibly moving flame and wick in close-up. Never request "
        "or describe balloons, landscapes, windmills, unrelated fire, invisible "
        "air visualizations or simulated footage. The observable flicker of "
        "the actual candle flame is evidence of changing air movement. "
        "All eight scenes need distinct, genuine filmed candle clips.\n"
    )

    # Pin only this run's subject AFTER the US picker installs. This ensures
    # the topic stays identical in generation, review and duplicate checking.
    original_install = montage_entry.us_trends.install

    def install_and_pin() -> None:
        original_install()
        trend_ideas._CACHE["everyday"] = topic
        trend_ideas._REFERENCES.pop("everyday", None)
        trend_ideas.pick_topic = lambda theme, fallback, model_json: topic

    montage_entry.us_trends.install = install_and_pin

    # The first production attempt chose 'hot air' search terms and received
    # hot-air balloons. Make EVERY query explicitly about a candle flame, while
    # keeping independent frame-level visual review and duplicate rejection.
    previous_plan = quality_entry.upgrade.generate_plan

    def candle_specific_plan():
        plan = previous_plan()
        for index, scene in enumerate(plan["scenes"]):
            scene["query"] = CANDLE_QUERIES[index % len(CANDLE_QUERIES)]
            scene["backup_queries"] = [
                CANDLE_BACKUPS[(index * 2) % len(CANDLE_BACKUPS)],
                CANDLE_BACKUPS[(index * 2 + 1) % len(CANDLE_BACKUPS)],
            ]
        print("ONE-OFF FOOTAGE SEARCH: candle-specific camera footage only", flush=True)
        return plan

    quality_entry.upgrade.generate_plan = candle_specific_plan
    print(f"ONE-OFF ORIGINAL SHORT: {topic}", flush=True)
    montage_entry.main()


if __name__ == "__main__":
    main()

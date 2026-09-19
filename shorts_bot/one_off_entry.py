"""Publish the user's requested airplane-window Short using the existing quality gates.

Only this one-off run is retargeted. The normal scheduled production code remains unchanged.
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
TOPIC = "why airplane windows are rounded"
REQUEST_ID = "curiorush-airplane-windows-2026-09-20"
WINDOW_QUERIES = (
    "airplane cabin oval window",
    "airplane window closeup",
    "passenger airplane window",
    "aircraft cabin windows",
    "airplane window view",
    "airplane interior windows",
    "plane window sky",
    "airplane cabin window",
)
WINDOW_BACKUPS = (
    "airplane oval window",
    "airplane window interior",
    "airplane cabin windows",
    "airplane window closeup",
    "aircraft window view",
    "airplane passenger window",
    "plane cabin windows",
    "airplane window sky",
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
    if request["request_id"] != REQUEST_ID:
        raise ValueError("Unexpected one-off request identifier")
    if request["theme"] != "everyday":
        raise ValueError("Unexpected one-off theme")
    topic = request["topic"]
    if topic != TOPIC or not re.fullmatch(r"[a-z ]{8,90}", topic):
        raise ValueError("Unexpected one-off topic")

    # The FAA's de Havilland Comet investigation identifies increased stress at
    # relatively squarish window corners and fatigue under pressurization.
    # The actual mechanism is not visible in ordinary window stock footage:
    # show a genuine rounded aircraft window, not a fake stress simulation or
    # supposedly authentic footage of a 1950s accident.
    editorial_upgrade.POLICY += (
        "\nAIRPLANE WINDOW ONE-OFF BRIEF: Explain why real passenger airplane windows "
        "have rounded or oval corners. Verified historical basis: the FAA's de "
        "Havilland Comet lessons-learned account identifies stress concentrated "
        "around squarish window corners, leading to metal fatigue during repeated "
        "cabin pressurization. State the takeaway simply: curved corners reduce "
        "stress concentration; do not claim they eliminate all stress or that "
        "every Comet failure began at a passenger window. Open with a concise "
        "question about rounded versus square windows; end with the actual "
        "engineering answer. Every scene must show authentic, relevant filmed "
        "airplane windows or an actual passenger cabin window view. The footage "
        "shows the observable window shape, NOT invisible mechanical stress, "
        "historical accidents, experiments, or a square window. Explain unseen "
        "stress in narration without pretending the stock shot visualizes it. "
        "No crash footage, unrelated aircraft exteriors, generic skies, fake "
        "animations, or invented historical claims. Keep the title concise and "
        "do not put generic hashtags or AI-tool mentions in the description.\n"
    )

    # Pin this one-off subject throughout script creation and duplicate checks.
    original_install = montage_entry.us_trends.install

    def install_and_pin() -> None:
        original_install()
        trend_ideas._CACHE["everyday"] = topic
        trend_ideas._REFERENCES.pop("everyday", None)
        trend_ideas.pick_topic = lambda theme, fallback, model_json: topic

    montage_entry.us_trends.install = install_and_pin

    # Prevent stock searches for abstract terms such as 'pressure' returning
    # pressure washers instead of an actual passenger airplane window.
    previous_plan = quality_entry.upgrade.generate_plan

    def airplane_window_plan():
        plan = previous_plan()
        for index, scene in enumerate(plan["scenes"]):
            scene["query"] = WINDOW_QUERIES[index % len(WINDOW_QUERIES)]
            scene["backup_queries"] = [
                WINDOW_BACKUPS[index % len(WINDOW_BACKUPS)],
                WINDOW_BACKUPS[(index + 3) % len(WINDOW_BACKUPS)],
            ]
        plan["title"] = "Why Are Airplane Windows Rounded?"
        plan["description"] = (
            "Why do airplane windows have curved corners? Discover the "
            "engineering reason behind their familiar shape. Everyday Mysteries."
        )
        plan["tags"] = ["airplane windows", "aviation", "aircraft engineering", "flight facts", "curiosity"]
        print("ONE-OFF FOOTAGE SEARCH: authentic aircraft window footage only", flush=True)
        return plan

    quality_entry.upgrade.generate_plan = airplane_window_plan
    print(f"ONE-OFF ORIGINAL SHORT: {topic}", flush=True)
    montage_entry.main()


if __name__ == "__main__":
    main()

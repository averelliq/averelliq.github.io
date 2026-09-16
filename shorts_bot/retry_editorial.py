"""One-off safe retry: regenerate rejected *plans*; never retry uploads.

Used only by the two remaining one-off Shorts jobs. Each attempt gets a new,
stock-friendly topic and production seed. All existing editorial/format checks
remain enabled; a successful upload is never retried.
"""
from __future__ import annotations

import os
import upgrade

_BASE_SEED = os.environ.get("GITHUB_RUN_ID", "local")
_TOPIC_CHOICES = {
    "history": (
        "the origins of the compass",
        "the history of the hourglass",
        "the history of the printing press",
        "ancient Roman aqueducts",
    ),
    "everyday": (
        "why popcorn pops",
        "why ice floats in water",
        "why soap bubbles are round",
        "how a zipper works",
    ),
}
_generate_once = upgrade.generate_plan
_previous_topic = upgrade.choose_topic


def regenerate_rejected_plan():
    theme = upgrade.select_theme()
    candidates = _TOPIC_CHOICES.get(theme)
    for attempt in range(1, 5):
        os.environ["GITHUB_RUN_ID"] = f"{_BASE_SEED}-editorial-attempt-{attempt}"
        if candidates:
            chosen = candidates[attempt - 1]
            upgrade.choose_topic = lambda selected_theme, current=chosen: (
                current if selected_theme == theme else _previous_topic(selected_theme)
            )
        try:
            plan = _generate_once()
            print(f"Plan accepted on attempt {attempt}", flush=True)
            return plan
        except SystemExit as exc:
            if attempt >= 4:
                raise
            print(f"Draft {attempt} rejected before video rendering or upload. Regenerating an independent topic; safety review remains enabled.", flush=True)
    raise RuntimeError("Editorial retries exhausted")


upgrade.generate_plan = regenerate_rejected_plan
upgrade.main()

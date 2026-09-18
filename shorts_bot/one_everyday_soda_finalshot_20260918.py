"""One-shot retry of original soda Short after previous final scene failed QC BEFORE upload.

Explicitly exclude unrelated ice-cube shot; preserve full final scene review.
"""
from __future__ import annotations

import selection_guard
import two_original_shorts_20260918 as pair


def main() -> None:
    plan = pair.PLANS["everyday"]
    plan["scenes"][0]["voiceover"] = "Soda bubbles are escaping gas. Why do they race upward?"
    # Original final QC rejected this clip as an ice-cube continuity break.
    selection_guard._USED_IDS.add(8676959)
    final = plan["scenes"][4]
    final["query"] = "soda bubbles macro"
    final["backup_queries"] = ["sparkling soda fizz", "carbonated drink bubbles closeup"]
    final["caption"] = "Bubbles reach the surface"
    pair.main("everyday")


if __name__ == "__main__":
    main()

"""Single corrected sunset Short after a confirmed no-upload final review failure.

Never rerun after an ambiguous YouTube upload response.
"""
from __future__ import annotations

import selection_guard
import two_original_shorts_20260918 as pair


def main() -> None:
    plan = pair.PLANS["viral"]
    # Original attempt was blocked by final QA: this Pexels clip prominently
    # contains ducks instead of a clear view of atmospheric sunset colors.
    selection_guard._USED_IDS.add(36318061)
    scene = plan["scenes"][2]
    scene["voiceover"] = (
        "Near sunset, the Sun sits low in the sky. Its light travels through more air."
    )
    scene["query"] = "sunset horizon clouds"
    scene["backup_queries"] = ["orange sunset sky", "sun low horizon"]
    scene["caption"] = "Light travels farther"
    pair.main("viral")


if __name__ == "__main__":
    main()

"""Enhanced scheduled Shorts with originality, licensed footage and final QC."""
from __future__ import annotations

import creator_guard
import editorial_upgrade
import gemini_transient_guard
import live_action_guard
import quality_entry
import montage_fx
import safe_captions
import us_trends


def main() -> None:
    editorial_upgrade.install()
    us_trends.install()
    gemini_transient_guard.install()
    # Only genuine camera footage; failed reviews mean NO publication.
    live_action_guard.install()
    safe_captions.install()
    creator_guard.install()
    # Also enforce final metadata on previews, not just public uploads.
    previous_validate = quality_entry.upgrade.validate_plan

    def validate_with_metadata(plan, theme):
        approved = previous_validate(plan, theme)
        creator_guard.metadata(approved)
        return approved

    quality_entry.upgrade.validate_plan = validate_with_metadata
    state = montage_fx.install(quality_entry)
    quality_entry.upgrade.main()
    print(
        "MONTAGE FX: "
        f"motion_clips={state['motion_clips']}, "
        f"animated_captions={state['animated_captions']}, "
        f"original_music={state['original_music']}, "
        "real_footage=True, original_script=True, short_titles=True, "
        "hashtags_in_description=False, duplicate_guard=True",
        flush=True,
    )


if __name__ == "__main__":
    main()

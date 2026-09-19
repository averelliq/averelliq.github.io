"""Original cloud Shorts: verify HD filmed footage before writing narration."""
from __future__ import annotations

import creator_guard
import editorial_upgrade
import footage_first
import gemini_transient_guard
import hd_footage_guard
import live_action_guard
import quality_entry
import montage_fx
import resilient_plan_guard
import safe_captions
import stock_recovery
import us_trends


def main() -> None:
    editorial_upgrade.install()
    us_trends.install()
    # Retry malformed scripts; never turn a negative review into approval.
    resilient_plan_guard.install()
    gemini_transient_guard.install()
    # Reject low resolution stock sources even if upscaling could make a 1080p file.
    hd_footage_guard.install()
    # Every additional stock candidate must pass the same independent reviews.
    stock_recovery.install()
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
    # Search, download, crop and independently inspect footage BEFORE script.
    # Preserve the existing scene-by-scene and final upload-blocking QC gates.
    footage_first.install()
    state = montage_fx.install(quality_entry)
    quality_entry.upgrade.main()
    print(
        "MONTAGE FX: "
        f"motion_clips={state['motion_clips']}, "
        f"animated_captions={state['animated_captions']}, "
        f"original_music={state['original_music']}, "
        "footage_first=True, real_footage=True, HD_source=True, original_script=True, "
        "short_titles=True, hashtags_in_description=False, duplicate_guard=True",
        flush=True,
    )


if __name__ == "__main__":
    main()

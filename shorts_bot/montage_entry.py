"""Original cloud Shorts: verify HD filmed footage before writing narration."""
from __future__ import annotations

import creator_guard
import editorial_upgrade
import footage_first
import footage_pool_fix
import footage_script_fix
import footage_review_fix
import gemini_transient_guard
import hd_footage_guard
import live_action_guard
import quality_entry
import montage_fx
import process_formats
import resilient_plan_guard
import safe_captions
import stock_recovery
import us_trends


def main() -> None:
    editorial_upgrade.install()
    us_trends.install()
    resilient_plan_guard.install()
    gemini_transient_guard.install()
    hd_footage_guard.install()
    stock_recovery.install()
    live_action_guard.install()
    safe_captions.install()
    creator_guard.install()
    previous_validate = quality_entry.upgrade.validate_plan

    def validate_with_metadata(plan, theme):
        approved = previous_validate(plan, theme)
        creator_guard.metadata(approved)
        return approved

    quality_entry.upgrade.validate_plan = validate_with_metadata
    footage_review_fix.install()
    footage_pool_fix.install()
    footage_first.install()
    footage_script_fix.install()
    process_formats.install()
    state = montage_fx.install(quality_entry)
    quality_entry.upgrade.main()
    print(
        "MONTAGE FX: "
        f"motion_clips={state['motion_clips']}, "
        f"animated_captions={state['animated_captions']}, "
        f"original_music={state['original_music']}, "
        "footage_first=True, process_formats=made/works/transformation, "
        "real_footage=True, native_HD_source=True, original_script=True, "
        "short_titles=True, hashtags_in_description=False, duplicate_guard=True",
        flush=True,
    )


if __name__ == "__main__":
    main()

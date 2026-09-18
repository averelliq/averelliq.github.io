"""Enhanced scheduled Shorts with original US curiosity editorial and filmed scene QC."""
from __future__ import annotations

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
    # Reject slides, vector art and unrelated footage. Failed QC means no upload.
    live_action_guard.install()
    safe_captions.install()
    state = montage_fx.install(quality_entry)
    quality_entry.upgrade.main()
    print(
        "MONTAGE FX: "
        f"motion_clips={state['motion_clips']}, "
        f"animated_captions={state['animated_captions']}, "
        f"original_music={state['original_music']}, "
        "real_footage=True, short_captions=True, original_US_topics=True",
        flush=True,
    )


if __name__ == "__main__":
    main()

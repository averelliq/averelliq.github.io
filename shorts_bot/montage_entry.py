"""Enhanced daily Shorts: filmed subjects only, independent scene QC."""
from __future__ import annotations

import live_action_guard
import quality_entry
import montage_fx


def main() -> None:
    # Reject illustrated, slide-like and screen-recorded candidates BEFORE upload.
    # The existing narration matching and independent final visual review remain.
    live_action_guard.install()
    state = montage_fx.install(quality_entry)
    quality_entry.upgrade.main()
    print(
        "MONTAGE FX: "
        f"motion_clips={state['motion_clips']}, "
        f"animated_captions={state['animated_captions']}, "
        f"original_music={state['original_music']}, "
        "live_action_required=True",
        flush=True,
    )


if __name__ == "__main__":
    main()

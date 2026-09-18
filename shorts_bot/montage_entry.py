"""Enhanced daily Shorts entrypoint; preserves existing editorial/visual safeguards."""
from __future__ import annotations

import quality_entry
import montage_fx


def main() -> None:
    state = montage_fx.install(quality_entry)
    quality_entry.upgrade.main()
    print(
        "MONTAGE FX: "
        f"motion_clips={state['motion_clips']}, "
        f"animated_captions={state['animated_captions']}, "
        f"original_music={state['original_music']}",
        flush=True,
    )


if __name__ == "__main__":
    main()

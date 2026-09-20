"""Preview only: use the native renderer and require manual audiovisual review.

The network Gemini visual review is not available in this workflow. Publishing
is explicitly forbidden; the preview exports real rendered frames for review.
"""
from __future__ import annotations

import os

import quality_entry
import pottery_preview_entry
import upgrade


def main() -> None:
    if os.environ.get("SHORTS_SKIP_UPLOAD") != "1":
        raise RuntimeError("Never bypass the final visual review in a publishing workflow")
    upgrade.aligned_build_video = quality_entry._original_build
    print("PREVIEW ONLY: use original HD/codec-checked renderer; inspect all 21 frames and MP4 before release", flush=True)
    pottery_preview_entry.main()


if __name__ == "__main__":
    main()

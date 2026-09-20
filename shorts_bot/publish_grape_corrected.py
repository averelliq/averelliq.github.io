"""Publish one independently reviewed corrected grape MP4, never a re-render.

The reviewed artifact and run are pinned; the shared publisher checks SHA256,
1080x1920 format, source provenance, 21 evidence frames and publication history.
"""
from __future__ import annotations

from pathlib import Path
import publish_six_reviewed as release

release.RUN_ID = 35492137791
release.APPROVAL = Path(__file__).resolve().parent / "grape_corrected_release.json"
release.ARTIFACTS = Path(__file__).resolve().parent / "grape_corrected_reviewed"
release.NAMES = {"grapes"}


def main():
    source = release.ARTIFACTS / f"curiorush-grape-corrected-{release.RUN_ID}"
    expected = release.ARTIFACTS / f"curiorush-six-grapes-{release.RUN_ID}"
    if not source.is_dir():
        raise RuntimeError("Missing corrected grape-only MP4 and 21 review frames")
    if not expected.exists():
        expected.symlink_to(source.name, target_is_directory=True)
    release.main()


if __name__ == "__main__":
    main()

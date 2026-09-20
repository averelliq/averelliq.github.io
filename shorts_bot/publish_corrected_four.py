"""Release only independently reviewed corrected four Short MP4 files."""
from __future__ import annotations

from pathlib import Path

import publish_six_reviewed as release

release.RUN_ID = 35482613532
release.APPROVAL = Path(__file__).resolve().parent / "four_shorts_release.json"
release.ARTIFACTS = Path(__file__).resolve().parent / "four_reviewed"

if __name__ == "__main__":
    release.main()

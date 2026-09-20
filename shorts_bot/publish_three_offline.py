"""Publish only independently reviewed exact three-topic preview MP4 files."""
from __future__ import annotations

from pathlib import Path

import publish_six_reviewed as release

release.RUN_ID = 35490083726
release.APPROVAL = Path(__file__).resolve().parent / "three_offline_release.json"
release.ARTIFACTS = Path(__file__).resolve().parent / "three_offline_reviewed"
release.NAMES = {"glass", "typewriter", "grapes"}

if __name__ == "__main__":
    release.main()

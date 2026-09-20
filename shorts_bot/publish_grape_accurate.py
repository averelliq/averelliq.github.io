"""Publish only independently visually approved grape-only MP4 once."""
from __future__ import annotations

from pathlib import Path
import publish_six_reviewed as release

release.RUN_ID = 35490968371
release.APPROVAL = Path(__file__).resolve().parent / 'grape_accurate_release.json'
release.ARTIFACTS = Path(__file__).resolve().parent / 'grape_accurate_reviewed'
release.NAMES = {'grapes'}


def main():
    source = release.ARTIFACTS / f'curiorush-grape-accurate-{release.RUN_ID}'
    expected = release.ARTIFACTS / f'curiorush-six-grapes-{release.RUN_ID}'
    if not source.is_dir():
        raise RuntimeError('Missing grape-only video or its 21 frames')
    if not expected.exists():
        expected.symlink_to(source.name, target_is_directory=True)
    release.main()


if __name__ == '__main__':
    main()

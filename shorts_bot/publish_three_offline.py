"""Release corrected glass and typewriter Shorts only after exact MP4 visual review.

The grape-juicing topic is deliberately excluded pending authentic process footage.
"""
from __future__ import annotations

from pathlib import Path

import publish_six_reviewed as release

release.RUN_ID = 35490586836
release.APPROVAL = Path(__file__).resolve().parent / 'three_offline_release.json'
release.ARTIFACTS = Path(__file__).resolve().parent / 'three_offline_reviewed'
release.NAMES = {'glass', 'typewriter'}


def main():
    for name in ('glass', 'typewriter'):
        source = release.ARTIFACTS / f'curiorush-curated-{name}-{release.RUN_ID}'
        expected = release.ARTIFACTS / f'curiorush-six-{name}-{release.RUN_ID}'
        if not source.is_dir():
            raise RuntimeError(f'Missing original corrected preview artifact: {name}')
        if not expected.exists():
            expected.symlink_to(source.name, target_is_directory=True)
    release.main()


if __name__ == '__main__':
    main()

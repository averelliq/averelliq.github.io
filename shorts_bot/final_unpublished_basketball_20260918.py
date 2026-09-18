"""Only basketball remains unpublished. NEVER rerun phone/pizza.

A previous final QC rejected scene five because an ordinary basketball shot could
not literally show heat and sound energy transfer. Describe the visible dribble
instead, with the flexible-shell explanation; preserve ALL mandatory gates.
"""
from __future__ import annotations

import three_us_original_shorts_20260918_evening as original
import two_us_remaining_visual_alignment_20260918 as previous


def main() -> None:
    previous.align()
    scenes = original.PLANS['basketball']['scenes']
    scenes[4].update({
        'voiceover': 'The flexible rubber shell springs back after impact, so another dribble can begin. One new mystery every day. Subscribe for more.',
        'query': 'basketball bouncing repeatedly',
        'backup_queries': ['basketball dribbling closeup', 'basketball bouncing court'],
        'caption': 'The ball springs back',
    })
    original.verify_all()
    original.main('basketball')


if __name__ == '__main__':
    main()

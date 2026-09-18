"""Publish ONLY the remaining basketball Short; never rerun phone or pizza.

Previous attempt stopped before rendering: unrelated pizza-plan validation failed.
Scope the script validation to the only video requested and keep all existing
candidate-footage, final-render review, caption and no-duplicate upload gates.
"""
from __future__ import annotations

import gemini_transient_guard
import three_us_original_shorts_20260918_evening as original
import two_original_shorts_20260918 as pair
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
    basketball = original.PLANS['basketball']
    pair.verify_script(basketball)
    if basketball['slug'] != 'why_basketballs_bounce_us_original':
        raise RuntimeError('Basketball-only upload guard: unexpected content')
    gemini_transient_guard.install()
    pair.PLANS['basketball'] = basketball
    pair.main('basketball')


if __name__ == '__main__':
    main()

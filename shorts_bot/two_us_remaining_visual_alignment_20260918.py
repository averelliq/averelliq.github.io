"""Only the TWO not-yet-published US Shorts. The phone Short was published already.

Correct scenes rejected by previous actual rendered-footage review; retain both
per-candidate and mandatory final visual review. No automatic retry of upload.
"""
from __future__ import annotations

import sys
import three_us_review_corrections_20260918 as old
import three_us_original_shorts_20260918_evening as original


def align() -> None:
    old.correct()
    basketball = original.PLANS['basketball']['scenes']
    basketball[2].update({
        'voiceover': 'A player dribbles the ball across the court, sending it down again and again.',
        'query': 'basketball player dribbling',
        'backup_queries': ['basketball court dribble', 'basketball playing court'],
        'caption': 'Watch the player dribble',
    })
    basketball[3].update({
        'voiceover': 'Each time the player dribbles, the ball rises toward the hand and drops again.',
        'query': 'basketball dribbling gym',
        'backup_queries': ['basketball handling ball', 'basketball dribble closeup'],
        'caption': 'Down, then up',
    })
    basketball[4].update({
        'voiceover': 'Some energy becomes heat and sound, so each bounce gets lower. One new mystery every day. Subscribe for more.',
        'query': 'basketball bouncing repeatedly',
        'backup_queries': ['basketball player dribbling', 'basketball bouncing gym'],
        'caption': 'Bounces lose some energy',
    })

    pizza = original.PLANS['pizza']['scenes']
    pizza[1].update({
        'voiceover': 'Warm mozzarella holds together, so melted cheese follows a freshly lifted pizza slice in strings.',
        'query': 'stretchy mozzarella pizza',
        'backup_queries': ['pizza slice cheese pull', 'mozzarella pizza closeup'],
        'caption': 'Warm mozzarella holds together',
    })
    pizza[2].update({
        'voiceover': 'Watch those long cheese strands stretch between the slice and the pizza before they finally break.',
        'query': 'hot pizza cheese stretch',
        'backup_queries': ['pizza mozzarella strings', 'pizza cheese pull closeup'],
        'caption': 'Long, stretchy cheese strands',
    })
    pizza[3].update({
        'voiceover': 'Another lifted slice shows that same stretchy cheese connecting the two pieces.',
        'query': 'pizza slice cheese pull',
        'backup_queries': ['stretchy melted pizza cheese', 'lifting pizza slice'],
        'caption': 'The cheese stays connected',
    })
    pizza[4].update({
        'voiceover': 'That famous cheesy pull is warm mozzarella holding together. One new mystery every day. Subscribe for more.',
        'query': 'pizza cheese strings',
        'backup_queries': ['pizza gooey cheese', 'pizza cheese stretch'],
        'caption': 'The famous cheese pull',
    })
    original.verify_all()


def main(category: str) -> None:
    if category not in ('basketball', 'pizza'):
        raise ValueError('Only unpublished basketball or pizza is allowed; phone already exists on YouTube')
    align()
    original.main(category)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Specify basketball or pizza ONLY')
    main(sys.argv[1])

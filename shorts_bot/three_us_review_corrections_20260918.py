"""Narrow, original-script corrections following mandatory first-run visual review.

Keep the live-action per-candidate AND final rendered-scene approval intact.
Each subject still must pass preflight, five unique clips and actual final review.
"""
from __future__ import annotations

import sys
import three_us_original_shorts_20260918_evening as original


def correct() -> None:
    basketball = original.PLANS['basketball']['scenes']
    basketball[2].update({
        'voiceover': 'Watch a basketball hit the floor and bounce right back toward the player.',
        'query': 'basketball dribbling court',
        'backup_queries': ['basketball bouncing floor', 'basketball player dribbling'],
        'caption': 'Watch the ball rebound',
    })
    basketball[3].update({
        'voiceover': 'The inflated ball springs back after impact, but it does not return quite as high.',
        'query': 'basketball bouncing gym',
        'backup_queries': ['basketball rebounding bounce', 'basketball dribbling gym'],
        'caption': 'It springs back up',
    })
    # Never claim that microscopic air compression is visually demonstrated by
    # ordinary external footage. The practical physics remains in title/description.
    basketball[4].update({
        'voiceover': 'Repeated bounces gradually get lower as energy becomes sound and heat. One new mystery every day. Subscribe for more.',
        'query': 'basketball bouncing repeatedly',
        'backup_queries': ['basketball dribbling closeup', 'basketball bouncing gym floor'],
        'caption': 'Bounces get lower',
    })

    pizza = original.PLANS['pizza']['scenes']
    # Prior rendered-scene review rejected these exact speech/footage mismatches:
    # scene four: a cutter served pizza, but narration claimed a cheese pull;
    # scene five: a box opened, but narration claimed cooling and change of stretch.
    pizza[3].update({
        'voiceover': 'Fresh pizza is sliced and served while its melted cheese is still warm.',
        'query': 'pizza cutting serving',
        'backup_queries': ['cutting fresh pizza', 'lifting pizza slice'],
        'caption': 'Fresh pizza is served',
    })
    pizza[4].update({
        'voiceover': 'Open the pizza box and there is the finished pie. One new mystery every day. Subscribe for more.',
        'query': 'opening pizza box',
        'backup_queries': ['pizza box opening', 'fresh pizza box'],
        'caption': 'Fresh pizza to share',
    })
    original.PLANS['pizza']['description'] = (
        'Why does hot mozzarella stretch on pizza? Its milk-protein network and melting behavior help create those strands. '
        'Original voiceover and independently checked filmed pizza footage. Everyday Mysteries. '
        'Source: https://agresearchmag.ars.usda.gov/2006/mar/foods/ #Shorts #Pizza #FoodScience'
    )
    original.verify_all()


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in original.PLANS:
        raise SystemExit('Specify phone, basketball or pizza')
    correct()
    original.main(sys.argv[1])

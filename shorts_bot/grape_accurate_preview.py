"""Grape-to-juice visual explanation, using ONLY seven verified Pexels grape videos.

Grape juice is released before any fermentation; winemaking pressing footage is
used ONLY to illustrate actual crushing, never presented as bottled fresh juice.
No automatic upload. Final footage and captions need separate visual review.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

import hd_footage_guard
import pottery_preview_entry as preview
import quality_entry
import upgrade

TOPIC = 'how grapes become fresh juice'
TITLE = 'How Grapes Release Juice'
DESCRIPTION = 'From picked grapes to the liquid inside—see what pressure does.'
CLIP_IDS = (5528415, 9947667, 28551137, 5944609, 35149891, 10505043, 9020878)
SPEECH = (
    'Grape juice starts with ripe grapes picked from the vine.',
    'Harvesters carefully pick bunches of fruit from the plant.',
    'The harvested grapes are gathered and carried for processing.',
    'The fruit is checked and handled before it is pressed.',
    'In larger facilities, conveyors help move grapes through processing.',
    'Crushing the fruit releases grape liquid, before any fermentation happens.',
    'Even a hand squeeze shows it: pressure breaks grapes and their juice escapes.',
)
CAPTIONS = ('Picked grapes', 'Harvesting', 'Collected fruit', 'Preparing grapes',
            'Processing', 'Press to release', 'Juice comes out')


def selected_clips():
    key = os.environ.get('PEXELS_API_KEY','').strip()
    if not key: raise RuntimeError('Missing licensed video source credentials')
    results = []
    for identifier in CLIP_IDS:
        response = requests.get(f'https://api.pexels.com/v1/videos/videos/{identifier}',
                                headers={'Authorization':key},timeout=40)
        response.raise_for_status()
        data = response.json()
        options = hd_footage_guard.hd_file_options(data)
        url = data.get('url','')
        if (data.get('id') != identifier or not isinstance(url,str) or
                not url.startswith('https://www.pexels.com/video/') or not options):
            raise ValueError(f'Grape-only source {identifier} lacks genuine native-HD provenance')
        results.append({'id':identifier,'query':'grape pressing harvested grape fruit',
                        'url':url,'links':options})
    print('GRAPE PREVIEW: all seven grape-only Pexels video IDs obtained by exact source lookup',flush=True)
    return results


def main():
    if os.environ.get('SHORTS_SKIP_UPLOAD') != '1':
        raise ValueError('Grape preview must never auto-publish')
    request = json.loads((Path(__file__).parent/'grape_accurate_request.json').read_text())
    if request.get('preview_only') is not True or request.get('topic') != TOPIC:
        raise ValueError('Unrecognized preview-only request')
    preview.TOPIC = TOPIC
    preview.SEARCHES = ('grape harvest', 'grape juice pressing')
    preview.SPEECH = SPEECH
    preview.CAPTIONS = CAPTIONS
    preview.collect = selected_clips
    preview.MAX_DOWNLOADS = 7
    upgrade.aligned_build_video = quality_entry._original_build
    preview.main()
    out = upgrade.bot.OUT
    plan_path = out/'plan.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if plan.get('topic') != TOPIC or len(plan.get('scenes',[])) != 7:
        raise ValueError('Grape-only scenes mismatch')
    plan.update(title=TITLE, description=DESCRIPTION,
                tags=['grapes','juice','how it works','fruit'],batch_topic='grapes')
    plan_path.write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    print('GRAPE PREVIEW READY: check 21 genuine frames and MP4 before publication',flush=True)


if __name__ == '__main__':main()

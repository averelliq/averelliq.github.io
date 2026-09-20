"""Grape-to-juice visual explanation with seven Pexels grape-only source videos.

The pressing footage illustrates liquid release BEFORE fermentation, not wine
as finished juice. Never auto-upload: exact MP4 and 21 frames need human review.
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
# The original fourth Pexels video (5944609) has no native-HD download option.
# 5945034 is already independently retrieved in our previous Pexels preview,
# and depicts a person handling a bunch of actual grapes.
CLIP_IDS = (5528415, 9947667, 28551137, 5945034, 35149891, 10505043, 9020878)
SPEECH = (
    'Grape juice starts with ripe grapes picked from the vine.',
    'Harvesters carefully pick bunches of fruit from the plant.',
    'The harvested grapes are gathered and carried for processing.',
    'The person handles individual grapes, still attached to the bunch.',
    'In larger facilities, conveyors help move grapes through processing.',
    'Crushing the fruit releases grape liquid, before any fermentation happens.',
    'Even a hand squeeze shows it: pressure breaks grapes and their juice escapes.',
)
CAPTIONS = ('Picked grapes', 'Harvesting', 'Collected fruit', 'Handling grapes',
            'Processing', 'Press to release', 'Juice comes out')


def selected_clips():
    key = os.environ.get('PEXELS_API_KEY','').strip()
    if not key:
        raise RuntimeError('Missing licensed video source credentials')
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
    print('GRAPE PREVIEW: seven source-verified native-HD Pexels grape videos ready',flush=True)
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
    print('GRAPE PREVIEW READY: check exact MP4 and actual 21 frames before release',flush=True)


if __name__ == '__main__':
    main()

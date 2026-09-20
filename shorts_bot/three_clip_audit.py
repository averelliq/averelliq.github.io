"""Export genuine Pexels source thumbnails and metadata for manual footage vetting.

The audit deliberately does not load the renderer, Gemini, voice engine, or uploader.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import requests


def topics():
    source = (Path(__file__).parent / 'three_offline_previews.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'CONFIG' for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('No static approved topic configuration')


def main():
    config = topics()
    name = os.environ.get('SHORTS_BATCH_TOPIC', '')
    if name not in config:
        raise ValueError('Unknown subject')
    key = os.environ.get('PEXELS_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Missing Pexels source API key')
    output = Path('shorts_bot/output/clip_audit') / name
    output.mkdir(parents=True, exist_ok=True)
    seen, rows = set(), []
    for query in config[name]['queries']:
        for page in (1, 2):
            response = requests.get('https://api.pexels.com/v1/videos/search',
                headers={'Authorization': key},
                params={'query': query, 'orientation': 'portrait', 'per_page': 30,
                        'page': page, 'locale': 'en-US'}, timeout=40)
            response.raise_for_status()
            for video in response.json().get('videos', []):
                ident, url, image = video.get('id'), video.get('url', ''), video.get('image', '')
                if (type(ident) is not int or ident in seen or
                    not isinstance(url, str) or not url.startswith('https://www.pexels.com/video/') or
                    not isinstance(image, str) or not image.startswith('https://')):
                    continue
                seen.add(ident)
                rows.append({'id': ident, 'url': url, 'query': query, 'thumbnail': image,
                             'duration': video.get('duration'), 'width': video.get('width'),
                             'height': video.get('height')})
                try:
                    result = requests.get(image, timeout=25)
                    result.raise_for_status()
                    (output / f'{ident}.jpg').write_bytes(result.content)
                except requests.RequestException:
                    pass
                if len(rows) >= 100:
                    break
            if len(rows) >= 100:
                break
        if len(rows) >= 100:
            break
    (output / 'candidates.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print(f'AUDIT {name}: {len(rows)} unique Pexels source records', flush=True)


if __name__ == '__main__':
    main()

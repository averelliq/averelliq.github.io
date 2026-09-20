"""Discover reviewable footage leads without claiming visual verification.

Pexels search is thematic, not an exact restoration-content classifier. The
previous strict URL-slug requirement yielded zero despite hundreds of results.
This module keeps strong metadata matches first, then offers a SMALL, clearly
labeled pool of weak matches for a human to watch. It never approves uploads.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
from pathlib import Path

import bot
import style_bot

MAX_CANDIDATES = 18
NEGATIVE = {'factory', 'industrial', 'warehouse', 'garage', 'cars', 'traffic',
            'junkyard', 'scrapyard', 'abandoned', 'wiping', 'washing', 'cleaning',
            'grinding', 'polishing', 'sanding', 'mechanic', 'mechanician', 'worker',
            'working', 'portrait', 'construction', 'fabrication', 'oil', 'pouring',
            'driving', 'parking', 'repairman'}
RESTORE = {'restoration', 'restore', 'restoring', 'restored', 'refurbishing',
           'refurbishment', 'refurbished', 'repair', 'repairing', 'repaired',
           'renovating', 'renovation'}


def score(video: dict, search_term: str) -> tuple[int, str]:
    """Prioritize clues, NOT a claim that the full restoration is in the video."""
    url = str(video.get('url') or '')
    path = urllib.parse.urlsplit(url)
    if path.hostname not in {'www.pexels.com', 'pexels.com'} or '/video/' not in path.path:
        return -100, 'invalid Pexels URL'
    slug = path.path.rstrip('/').split('/')[-1]
    words = set(re.findall(r'[a-z]+', slug.lower()))
    if words & NEGATIVE and not words & RESTORE:
        return -100, 'generic workshop or isolated action'
    if words & {'ai', 'generated', 'animation', 'slideshow'}:
        return -100, 'not verified live footage'
    explicit = bool(words & RESTORE or any(w.startswith(('restor', 'refurbish')) for w in words))
    worn = bool(words & style_bot.WEAR)
    obj = bool(words & style_bot.OBJECT)
    if explicit and (worn or obj):
        return 100 + int(worn) * 10 + int(obj) * 5, 'restoration wording in URL; video still unverified'
    if explicit:
        return 70, 'restoration wording in URL; object and outcome unverified'
    if worn and obj:
        return 38, 'worn object in URL; restoration process unverified'
    if obj and not words & NEGATIVE:
        return 12, 'object in URL; restoration and before/after unverified'
    return 0, 'search-query match only; likely weak relevance'


def discover(output: Path) -> None:
    found: dict[int, dict] = {}
    examined: set[int] = set()
    for term in style_bot.SEARCH_TERMS:
        for page in (1, 2):
            response = bot.pexels_json('/search', {'query': term, 'per_page': 30, 'page': page})
            for video in response.get('videos', []):
                ident = video.get('id')
                if type(ident) is not int or ident <= 0:
                    continue
                examined.add(ident)
                duration = int(video.get('duration') or 0)
                if not 30 <= duration <= 600 or not video.get('video_files'):
                    continue
                rank, reason = score(video, term)
                if rank < 0:
                    continue
                existing = found.get(ident)
                if existing and existing['metadata_rank'] >= rank:
                    continue
                found[ident] = {
                    'id': ident, 'duration': duration, 'url': video.get('url'),
                    'preview': video.get('image'),
                    'photographer': (video.get('user') or {}).get('name'),
                    'search_term': term, 'metadata_rank': rank,
                    'why_listed': reason,
                    'review_status': 'UNVERIFIED FOOTAGE LEAD — NOT APPROVED',
                    'requires_manual_visual_and_rights_review': True,
                    'review_checklist': list(style_bot.CHECKLIST),
                }
            if not response.get('next_page'):
                break
    ranked = sorted(found.values(), key=lambda entry: (-entry['metadata_rank'], entry['id']))
    strong = [entry for entry in ranked if entry['metadata_rank'] >= 70]
    weak = [entry for entry in ranked if 0 < entry['metadata_rank'] < 70]
    # Do not call a random search match an actual restoration candidate.
    selected = (strong + weak)[:MAX_CANDIDATES]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(selected, indent=2, ensure_ascii=False), encoding='utf-8')
    report = {
        'unique_results_examined': len(examined),
        'metadata_restoration_leads': len(strong),
        'weak_review_leads': len(weak),
        'review_links_exported': len(selected),
        'visually_verified': 0, 'approved_for_reuse': 0,
        'warning': ('A search term, stock footage URL, or thumbnail cannot prove before/process/after, '
                    'same-object continuity, authenticity, or reuse permissions. Review the full video.'),
    }
    (output.parent / 'review_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    entries = []
    for index, video in enumerate(selected, 1):
        url = html.escape(str(video['url']), quote=True)
        image = html.escape(str(video.get('preview') or ''), quote=True)
        reason = html.escape(video['why_listed'])
        entries.append(f'<article><a href="{url}" target="_blank" rel="noopener noreferrer">'
                       f'<img src="{image}" loading="lazy" alt="Stock clip preview">'
                       f'<h2>#{index} — {video["duration"]} sec — Watch source</h2></a>'
                       f'<p>{reason}. NOT visually verified. Check the full process and rights.</p></article>')
    gallery = ('<!doctype html><html lang="en"><meta charset="utf-8">'
               '<meta name="viewport" content="width=device-width,initial-scale=1">'
               '<title>Restoration footage review leads</title>'
               '<style>body{font:16px system-ui;margin:24px;max-width:1200px}'
               'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}'
               'article{border:1px solid #bbb;border-radius:12px;padding:12px}'
               'img{width:100%;height:180px;object-fit:cover}</style>'
               '<h1>Unverified restoration footage leads</h1>'
               '<p>These are possible videos to WATCH, not approved restoration videos or permission to repost.</p>'
               '<main>' + ''.join(entries) + '</main></html>')
    (output.parent / 'review_gallery.html').write_text(gallery, encoding='utf-8')
    print(f'Examined {len(examined)} clips; exported {len(selected)} UNVERIFIED viewing links '
          f'({len(strong)} stronger metadata leads, {len(weak)} weak leads); 0 visually verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['discover'])
    parser.add_argument('--output', type=Path, default=Path('output/candidates.json'))
    args = parser.parse_args()
    discover(args.output)

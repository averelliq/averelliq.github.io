"""Create one of three genuinely new original Shorts, preview-only and fail-closed.

The existing footage-first pipeline MUST verify eight distinct filmed native-HD
Pexels clips before scripting, then validate each scene and the encoded video.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUEST = ROOT / 'three_fresh_request.json'
CANDIDATES = {
    'craft': [
        ('how candles are poured into jars', (
            'candle making wax pouring', 'soy candle making', 'pouring candle wax',
            'handmade candle workshop', 'candle maker pouring wax')),
        ('how handmade chocolate bars are molded', (
            'chocolate tempering', 'chocolate making mold', 'chocolate factory pouring',
            'artisan chocolate bars', 'chocolate maker workshop')),
    ],
    'mechanics': [
        ('how a bicycle gear changes', (
            'bicycle gear shifting closeup', 'bike derailleur moving chain',
            'bicycle chain gears', 'bicycle repair derailleur', 'bicycle cassette spinning')),
        ('how an automatic car wash cleans a car', (
            'automatic car wash brushes', 'car wash machine', 'car washing foam',
            'car wash tunnel', 'automatic car wash')),
    ],
    'workshop': [
        ('how a wood lathe shapes a bowl', (
            'woodturning bowl lathe', 'wood lathe workshop', 'woodturning close up',
            'woodworking lathe bowl', 'woodturner shaving wood')),
        ('how a traditional printing press works', (
            'letterpress printing machine', 'printing press working',
            'letterpress workshop', 'printing machine paper', 'traditional printing press')),
    ],
}


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in CANDIDATES:
        raise ValueError('Specify a unique topic group')
    group = sys.argv[1]
    request = json.loads(REQUEST.read_text(encoding='utf-8'))
    if (request != {'request_id': 'curiorush-three-new-topics-20260920-01',
                    'preview_only': True, 'groups': list(CANDIDATES)}
            or os.getenv('SHORTS_SKIP_UPLOAD') != '1'
            or os.getenv('GITHUB_EVENT_NAME') != 'push'
            or os.getenv('GITHUB_REPOSITORY') != 'averelliq/averelliq.github.io'):
        raise RuntimeError('Invalid reviewed-only request; no upload')
    if any(os.getenv(k) for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN')):
        raise RuntimeError('YouTube OAuth secrets must NEVER be in a preview run')
    if not (os.getenv('PEXELS_API_KEY') and os.getenv('GEMINI_API_KEY')):
        raise RuntimeError('Real filmed source or independent visual reviewer unavailable')
    import footage_first
    import montage_entry
    import trend_ideas
    import upgrade

    topic_candidates = CANDIDATES[group]
    # Override only topic discovery: all real-footage, audio, originality and
    # matching-scene checks in montage_entry remain in force.
    footage_first._seed = lambda theme: topic_candidates[0][0]
    footage_first._candidates = lambda theme, seed: list(topic_candidates)
    trend_ideas.pick_topic = lambda theme, fallback, model_json: topic_candidates[0][0]
    print(f'NEW SHORTS PREVIEW {group}: permitted subjects {[x[0] for x in topic_candidates]}', flush=True)
    montage_entry.main()

    output = ROOT / 'output'
    movie = output / 'short.mp4'
    plan = json.loads((output / 'plan.json').read_text(encoding='utf-8'))
    sources = json.loads((output / 'visual_sources.json').read_text(encoding='utf-8'))
    ids = [item.get('pexels_video_id') for item in sources]
    if (plan.get('topic') not in {x[0] for x in topic_candidates}
            or len(plan.get('scenes', [])) != 8 or len(ids) != 8
            or any(type(x) is not int or x <= 0 for x in ids)
            or len(set(ids)) != 8
            or not all(s.get('footage_verified_before_script') is True
                       and str(s.get('stock_source_url', '')).startswith('https://www.pexels.com/video/')
                       for s in plan['scenes'])):
        raise ValueError('Wrong/previous subject, missing genuine footage, or duplicate video scenes')
    info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                           '-of', 'json', str(movie)]).stdout)
    vids = [s for s in info['streams'] if s.get('codec_type') == 'video']
    auds = [s for s in info['streams'] if s.get('codec_type') == 'audio']
    duration = float(info['format']['duration'])
    if (len(vids) != 1 or len(auds) != 1
            or vids[0].get('width') != 1080 or vids[0].get('height') != 1920
            or vids[0].get('codec_name') != 'h264' or auds[0].get('codec_name') != 'aac'
            or not 20 <= duration <= 58):
        raise ValueError('Final video, audio, aspect ratio or codec quality failure')
    run(['ffmpeg', '-v', 'error', '-i', str(movie), '-f', 'null', '-'])
    # A like-and-subscribe overlay must be added by cta_overlay and the real
    # encoded frame must exist; failing to add it prevents approval.
    ass = ROOT / 'work' / 'captions.ass'
    if not ass.is_file() or 'LIKE  +  SUBSCRIBE' not in ass.read_text(encoding='utf-8'):
        raise ValueError('Requested visible LIKE + SUBSCRIBE CTA absent')
    for index, seconds in enumerate(plan.get('scene_durations', [])):
        stamp = sum(plan['scene_durations'][:index]) + float(seconds) * .5
        run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{stamp:.3f}', '-i', str(movie),
             '-frames:v', '1', '-vf', 'scale=405:720',
             str(output / f'scene_{index + 1:02d}.jpg')])
    run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{duration * .68 + .7:.3f}',
         '-i', str(movie), '-frames:v', '1', str(output / f'{group}_cta_proof.jpg')])
    plan['preview_only'] = True
    plan['batch_topic'] = group
    plan['final_mp4_decoded'] = True
    plan['cta'] = 'LIKE + SUBSCRIBE overlay present'
    (output / 'plan.json').write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding='utf-8')
    (output / 'manual_review_required.txt').write_text(
        'Preview only: examine actual MP4 visuals, factual alignment, captions and audio. '
        'No YouTube upload permitted in this run.\n', encoding='utf-8')
    print(f'PREVIEW QC PASSED {group}: {plan["topic"]}; eight different live-action '
          f'Full HD clips; {duration:.2f}s; 1080x1920; CTA present; NO UPLOAD', flush=True)


if __name__ == '__main__':
    main()

"""Example-style restoration discovery and three-stage Shorts editing (human reviewed)."""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import urllib.parse
from pathlib import Path

import bot

SEARCH_TERMS = (
    'rusty iron restoration', 'rusty tool restoration', 'antique iron restoration',
    'rusty axe restoration', 'old knife restoration', 'rusty hand tool restoration',
    'antique metal restoration', 'vintage appliance restoration',
    'rust removal restoration', 'before after restoration',
)
WEAR = {'rust', 'rusty', 'rusted', 'corroded', 'antique', 'vintage', 'old', 'worn'}
OBJECT = {'iron', 'tool', 'axe', 'knife', 'saw', 'plane', 'hammer', 'wrench', 'drill',
          'metal', 'machine', 'appliance', 'kettle', 'lock', 'lamp', 'scissors', 'razor'}
CHECKLIST = (
    'Old, rusty or clearly worn object at the beginning',
    'Moving, hands-on rust removal, disassembly, sanding, repair or reassembly',
    'Clear final reveal of the SAME restored object, preferably in use',
    'No unrelated workshop B-roll or still-image slideshow',
    'No burned-in subtitles/watermarks; confirm footage rights and credit',
)


def metadata_looks_like_restoration(url: str) -> bool:
    """Only a conservative URL prefilter; not proof of the video contents."""
    slug = urllib.parse.urlsplit(url or '').path.rstrip('/').split('/')[-1]
    words = set(re.findall(r'[a-z]+', slug.lower()))
    return (any(word.startswith(('restor', 'refurbish', 'renovat')) for word in words)
            and bool(words & (WEAR | OBJECT)))


def discover(output: Path) -> None:
    candidates, seen = {}, set()
    for term in SEARCH_TERMS:
        for page in (1, 2):
            response = bot.pexels_json('/search', {'query': term, 'per_page': 30, 'page': page})
            for video in response.get('videos', []):
                ident = video.get('id')
                if type(ident) is not int or ident <= 0 or ident in seen:
                    continue
                seen.add(ident)
                duration = int(video.get('duration') or 0)
                if not 45 <= duration <= 240 or not video.get('video_files'):
                    continue
                if not metadata_looks_like_restoration(str(video.get('url') or '')):
                    continue
                candidates[ident] = {
                    'id': ident, 'duration': duration, 'url': video.get('url'),
                    'photographer': (video.get('user') or {}).get('name'),
                    'preview': video.get('image'), 'search_term': term,
                    'review_status': 'UNVERIFIED: metadata match only',
                    'review_checklist': list(CHECKLIST),
                    'requires_manual_visual_and_rights_review': True,
                }
            if not response.get('next_page'):
                break
    results = list(candidates.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    report = {'style': 'rusty object -> hands-on restoration -> final SAME object',
              'searched_terms': list(SEARCH_TERMS), 'unique_results_examined': len(seen),
              'unverified_candidates': len(results), 'visually_verified': 0,
              'warning': 'URL metadata cannot prove the video contains complete restoration. Zero is a valid result.'}
    (output.parent / 'review_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    blocks = []
    for index, video in enumerate(results, 1):
        url, image = (html.escape(str(video[field] or ''), quote=True) for field in ('url', 'preview'))
        blocks.append(f'<article><a href="{url}" target="_blank" rel="noopener noreferrer">'
                      f'<img src="{image}" alt="Candidate {index} preview" loading="lazy">'
                      f'<h2>#{index} · {video["duration"]} seconds · Watch</h2></a>'
                      f'<p>Pexels ID {video["id"]}. UNVERIFIED: inspect beginning, work, end, same object and rights.</p></article>')
    page = ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Example-style restoration review queue</title><style>'
            'body{font:16px system-ui;margin:1.5rem;max-width:1100px}'
            'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem}'
            'article{border:1px solid #aaa;border-radius:12px;padding:12px}'
            'img{width:100%;height:180px;object-fit:cover}a{color:inherit}</style>'
            '<h1>Unverified restoration candidates</h1><p>Metadata matches only. '
            'Watch the entire source video before approving.</p><main>' + ''.join(blocks) + '</main></html>')
    (output.parent / 'review_gallery.html').write_text(page, encoding='utf-8')
    print(f'Examined {len(seen)} unique clips; found {len(results)} UNVERIFIED metadata candidates. '
          'No clip has been visually verified or uploaded.')


def validate_manifest(data: dict) -> dict:
    bot.validate_manifest(data)
    for flag in ('rusty_or_worn_start', 'hands_on_restoration',
                 'same_object_in_final', 'moving_footage'):
        if data.get(flag) is not True:
            raise ValueError(f'Example-style human review requires {flag}=true')
    segments = data.get('segments')
    if not isinstance(segments, list) or not 3 <= len(segments) <= 9:
        raise ValueError('Provide 3-9 reviewed segments: before, process, after')
    stages = [item.get('stage') if isinstance(item, dict) else None for item in segments]
    if stages[0] != 'before' or stages[-1] != 'after' or any(s != 'process' for s in stages[1:-1]):
        raise ValueError('Segments must run before -> process -> after')
    previous_end = 0.0
    for item in segments:
        start, length = item.get('start_seconds'), item.get('duration_seconds')
        if (type(start) not in (int, float) or type(length) not in (int, float)
                or start < previous_end - .01 or length < .5):
            raise ValueError('Segments must be chronological and nonoverlapping, each at least 0.5s')
        previous_end = start + length
    if not 2 <= segments[0]['duration_seconds'] <= 8 or not 3 <= segments[-1]['duration_seconds'] <= 12:
        raise ValueError('Use a 2-8s before and 3-12s final reveal')
    if abs(sum(item['duration_seconds'] for item in segments) - data.get('target_seconds', 45)) > .05:
        raise ValueError('Segment lengths must sum to target_seconds')
    return data


def narration(data: dict) -> str:
    item = data['item'].strip().rstrip('.')
    steps = [step.strip().rstrip('. ') for step in data['observed_steps']]
    transitions = ('First, ', 'Next, ', 'Then, ', 'After that, ', 'Now, ', 'Finally, ')
    middle = ' '.join(f'{transitions[i]}{step[0].lower() + step[1:]}.' for i, step in enumerate(steps))
    return f'Watch this {item} get a second life. {middle} Here is the restored {item}. What should be next?'


def montage_filter(segments: list[dict]) -> str:
    chains = []
    for i, item in enumerate(segments):
        chains.append(f'[0:v:0]trim=start={item["start_seconds"]}:duration={item["duration_seconds"]},'
                      'setpts=PTS-STARTPTS,fps=30,scale=1080:1920:force_original_aspect_ratio=increase,'
                      f'crop=1080:1920,setsar=1[v{i}]')
    return ';'.join(chains + [f'{"".join(f"[v{i}]" for i in range(len(segments)))}'
                              f'concat=n={len(segments)}:v=1:a=0[v]'])


def render(manifest: Path, output_dir: Path, upload: bool) -> None:
    if (not manifest.is_file() or manifest.suffix.lower() != '.json'
            or manifest.parent.resolve() != Path('approved').resolve()):
        raise ValueError('Manifest must be in approved/ as JSON')
    data = validate_manifest(json.loads(manifest.read_text(encoding='utf-8')))
    output_dir.mkdir(parents=True, exist_ok=True)
    video = bot.pexels_json('/videos/' + str(data['pexels_video_id']))
    if int(video.get('id') or 0) != data['pexels_video_id']:
        raise ValueError('Pexels video ID mismatch')
    last_frame = max(s['start_seconds'] + s['duration_seconds'] for s in data['segments'])
    if float(video.get('duration') or 0) < last_frame:
        raise ValueError('Source video is too short for approved before/process/after segments')
    source, audio, output = (output_dir / name for name in ('source.mp4', 'narration.mp3', 'short.mp4'))
    bot.download_mp4(bot.select_mp4(video), source)
    source_info = bot.probe(source)
    if (not any(s.get('codec_type') == 'video' for s in source_info.get('streams', []))
            or float(source_info['format']['duration']) < last_frame):
        raise ValueError('Downloaded video lacks required frames')
    script = narration(data)
    (output_dir / 'script.txt').write_text(script, encoding='utf-8')
    asyncio.run(bot.synthesize(script, audio))
    length = float(data.get('target_seconds', 45))
    if float(bot.probe(audio)['format']['duration']) > length - 1:
        raise ValueError('English narration is too long; shorten accurately observed steps')
    # The source video is mapped WITHOUT its original audio, subtitle or metadata streams.
    bot.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source), '-i', str(audio),
             '-filter_complex', montage_filter(data['segments']), '-map', '[v]', '-map', '1:a:0',
             '-t', str(length), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
             '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-af', 'apad',
             '-movflags', '+faststart', str(output)])
    rendered = bot.probe(output)
    seconds = float(rendered['format']['duration'])
    if not 39.5 <= seconds <= 50.5 or not any(s.get('codec_type') == 'audio' for s in rendered['streams']):
        raise ValueError('Rendered Shorts duration or narration failed final checks')
    (output_dir / 'source-info.json').write_text(json.dumps({
        'source_url': video.get('url'), 'creator': (video.get('user') or {}).get('name'),
        'duration_seconds': seconds, 'reviewed_segments': data['segments']}, indent=2), encoding='utf-8')
    print(f'Example-style 1080x1920 Short ready: {output}; {seconds:.1f}s')
    if upload:
        bot.upload_private(output, data, video)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('discover').add_argument('--output', type=Path, default=Path('output/candidates.json'))
    rendering = commands.add_parser('render')
    rendering.add_argument('--manifest', type=Path, required=True)
    rendering.add_argument('--output', type=Path, default=Path('output'))
    rendering.add_argument('--upload-private', action='store_true')
    args = parser.parse_args()
    if args.command == 'discover':
        discover(args.output)
    else:
        render(args.manifest, args.output, args.upload_private)


if __name__ == '__main__':
    main()

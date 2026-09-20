"""License-aware restoration Shorts discovery, rendering, and optional private upload."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

API = 'https://api.pexels.com/v1/videos'
SEARCH_TERMS = ('rust restoration', 'tool restoration', 'antique restoration', 'metal polishing', 'repair workshop')


def pexels_json(path: str, query: dict | None = None) -> dict:
    key = os.environ.get('PEXELS_API_KEY')
    if not key:
        raise RuntimeError('PEXELS_API_KEY GitHub Actions secret is missing')
    url = API + path + ('?' + urllib.parse.urlencode(query) if query else '')
    req = urllib.request.Request(url, headers={'Authorization': key, 'User-Agent': 'restoration-shorts-bot/1.0'})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp)


def discover(output: Path) -> None:
    videos = {}
    for term in SEARCH_TERMS:
        for video in pexels_json('/search', {'query': term, 'per_page': 30}).get('videos', []):
            duration = int(video.get('duration') or 0)
            if 40 <= duration <= 90 and video.get('video_files'):
                videos[video['id']] = {
                    'id': video['id'], 'duration': duration, 'url': video.get('url'),
                    'photographer': (video.get('user') or {}).get('name'),
                    'preview': video.get('image'), 'search_term': term,
                    'requires_manual_visual_and_rights_review': True,
                }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(list(videos.values()), indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Found {len(videos)} candidates; none is automatically approved or published.')


def validate_manifest(data: dict) -> dict:
    if data.get('source') != 'pexels' or not isinstance(data.get('pexels_video_id'), int) or data['pexels_video_id'] <= 0:
        raise ValueError('Only a verified positive Pexels video ID is accepted')
    if data.get('human_reviewed') is not True or data.get('rights_reviewed') is not True:
        raise ValueError('Human footage review and rights review are required')
    if data.get('burned_in_captions_or_watermark') is not False:
        raise ValueError('Select a clean video; embedded text or watermark cannot be reliably removed')
    if data.get('visible_before_and_after') is not True:
        raise ValueError('This workflow requires a visible before-and-after restoration')
    title = data.get('title')
    item = data.get('item')
    steps = data.get('observed_steps')
    if not isinstance(title, str) or not 8 <= len(title) <= 80 or not isinstance(item, str) or not 3 <= len(item) <= 65:
        raise ValueError('Provide a specific English title and item name')
    if not isinstance(steps, list) or not 3 <= len(steps) <= 6 or not all(isinstance(x, str) and 8 <= len(x) <= 130 for x in steps):
        raise ValueError('Provide 3-6 genuinely observed steps, in English')
    if not isinstance(data.get('start_seconds', 0), (int, float)) or not 0 <= data.get('start_seconds', 0) <= 30:
        raise ValueError('Invalid clip start')
    if not isinstance(data.get('target_seconds', 45), (int, float)) or not 40 <= data.get('target_seconds', 45) <= 50:
        raise ValueError('Video must be 40-50 seconds')
    return data


def narration(data: dict) -> str:
    item = data['item'].strip().rstrip('.')
    stages = [s.strip().rstrip('. ') for s in data['observed_steps']]
    opening = f'This {item} looked ready for the scrap heap. But watch what happens when the restoration begins.'
    transitions = ['First, ', 'Next, ', 'Then, ', 'After that, ', 'Now, ', 'Finally, ']
    middle = ' '.join(f'{transitions[i]}{step[0].lower() + step[1:]}.' for i, step in enumerate(stages))
    ending = f'The difference is incredible. From worn out to renewed, this {item} gets a second life. Which restoration should we show next?'
    return f'{opening} {middle} {ending}'


def select_mp4(video: dict) -> str:
    choices = [v for v in video.get('video_files', []) if v.get('file_type') == 'video/mp4'
               and v.get('link', '').startswith('https://') and (v.get('width') or 0) >= 720]
    if not choices:
        raise ValueError('No HD MP4 available on this Pexels entry')
    return max(choices, key=lambda v: (min(v.get('width') or 0, v.get('height') or 0), v.get('width') or 0))['link']


def download_mp4(url: str, output: Path, max_bytes: int = 300_000_000) -> None:
    # URLs are taken only from Pexels's authenticated API response, never user input.
    req = urllib.request.Request(url, headers={'User-Agent': 'restoration-shorts-bot/1.0'})
    with urllib.request.urlopen(req, timeout=60) as response, output.open('wb') as dst:
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError('Input video exceeds download size limit')
            dst.write(chunk)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
          'format=duration:stream=codec_type,width,height', '-of', 'json', str(path)], text=True))


async def synthesize(text: str, output: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice=os.getenv('ENGLISH_VOICE', 'en-US-GuyNeural'), rate='-5%').save(str(output))


def render(manifest: Path, output_dir: Path, upload: bool) -> None:
    if not manifest.is_file() or manifest.suffix.lower() != '.json' or manifest.parent.resolve() != Path('approved').resolve():
        raise ValueError('Manifest must be an existing JSON file inside the approved/ directory')
    data = validate_manifest(json.loads(manifest.read_text(encoding='utf-8')))
    output_dir.mkdir(parents=True, exist_ok=True)
    video = pexels_json('/videos/' + str(data['pexels_video_id']))
    if int(video.get('id') or 0) != data['pexels_video_id']:
        raise RuntimeError('Pexels video ID mismatch')
    if int(video.get('duration') or 0) < float(data.get('start_seconds', 0)) + float(data.get('target_seconds', 45)):
        raise ValueError('Source footage is too short for the chosen range')
    source = output_dir / 'source.mp4'
    audio = output_dir / 'narration.mp3'
    output = output_dir / 'short.mp4'
    download_mp4(select_mp4(video), source)
    source_probe = probe(source)
    if not any(s.get('codec_type') == 'video' for s in source_probe.get('streams', [])):
        raise ValueError('Downloaded media has no video stream')
    script = narration(data)
    (output_dir / 'script.txt').write_text(script, encoding='utf-8')
    asyncio.run(synthesize(script, audio))
    voice_duration = float(probe(audio)['format']['duration'])
    duration = float(data.get('target_seconds', 45))
    if voice_duration > duration - 1.0:
        raise ValueError(f'Narration too long ({voice_duration:.1f}s); simplify observed steps and retry')
    # Re-encode only video stream; audio/subtitle/data streams are not mapped.
    filter_video = 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
         '-ss', str(data.get('start_seconds', 0)), '-i', str(source), '-i', str(audio),
         '-filter_complex', f'[0:v:0]{filter_video}[v]', '-map', '[v]', '-map', '1:a:0',
         '-t', str(duration), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
         '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
         '-af', 'apad', '-movflags', '+faststart', str(output)])
    result = probe(output)
    actual = float(result['format']['duration'])
    if not 39.5 <= actual <= 50.5:
        raise RuntimeError(f'Unexpected output duration: {actual:.2f}s')
    if not any(s.get('codec_type') == 'audio' for s in result.get('streams', [])):
        raise RuntimeError('No English narration in final video')
    (output_dir / 'source-info.json').write_text(json.dumps({'pexels_url': video.get('url'),
        'photographer': (video.get('user') or {}).get('name'), 'duration': actual}, indent=2), encoding='utf-8')
    print(f'Created {output}: {actual:.1f}s. Uploaded: {upload}')
    if upload:
        upload_private(output, data, video)


def upload_private(path: Path, data: dict, source: dict) -> None:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    needed = ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN')
    missing = [name for name in needed if not os.getenv(name)]
    if missing:
        raise RuntimeError('Missing YouTube OAuth GitHub secrets: ' + ', '.join(missing))
    creds = Credentials(token=None, refresh_token=os.environ['YT_REFRESH_TOKEN'],
        token_uri='https://oauth2.googleapis.com/token', client_id=os.environ['YT_CLIENT_ID'],
        client_secret=os.environ['YT_CLIENT_SECRET'], scopes=['https://www.googleapis.com/auth/youtube.upload'])
    youtube = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    description = (f"Restoration process explained in English.\n\n"
        f"Original footage: {source.get('url', '')}\n"
        f"Footage creator: {(source.get('user') or {}).get('name', 'Pexels contributor')}\n"
        'Footage via Pexels: https://www.pexels.com/\n'
        'Original narration and editing by this channel. #restoration #shorts')
    request = youtube.videos().insert(part='snippet,status', body={
        'snippet': {'title': data['title'], 'description': description, 'categoryId': '26'},
        'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False}},
        media_body=MediaFileUpload(str(path), mimetype='video/mp4', resumable=True))
    result = None
    while result is None:
        _, result = request.next_chunk()
    print('PRIVATE YouTube upload completed. Video ID:', result['id'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    discovery = sub.add_parser('discover')
    discovery.add_argument('--output', type=Path, default=Path('output/candidates.json'))
    generation = sub.add_parser('render')
    generation.add_argument('--manifest', type=Path, required=True)
    generation.add_argument('--output', type=Path, default=Path('output'))
    generation.add_argument('--upload-private', action='store_true')
    args = parser.parse_args()
    if args.command == 'discover':
        discover(args.output)
    else:
        render(args.manifest, args.output, args.upload_private)


if __name__ == '__main__':
    main()

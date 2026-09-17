"""TEST ONLY: exercise real MPT CLI with approved tok SAMPLE and three dummy cards.

This does not approve the placeholder visuals or a full-length narration.
No API keys, voice cloning, paid AI provider, or YouTube upload is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont
import mpt_bridge
from voice_preview_v6 import SAMPLE

APPROVED_TOK_SHA256 = '586244cd639faf5fd5995d1f4a9e74c4bceb7a88852075eee8d046274ea9528b'


def run(workspace: Path, upstream: Path, audio: Path) -> dict:
    workspace, upstream, audio = workspace.resolve(), upstream.resolve(), audio.resolve(strict=True)
    if upstream != (workspace / 'upstream' / 'MoneyPrinterTurbo').resolve():
        raise ValueError('Untrusted upstream path')
    commit = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != mpt_bridge.UPSTREAM_COMMIT or not (upstream / 'LICENSE').is_file():
        raise ValueError('MoneyPrinterTurbo version or MIT license mismatch')
    if hashlib.sha256(audio.read_bytes()).hexdigest() != APPROVED_TOK_SHA256:
        raise ValueError('Approved tok audition WAV mismatch; no fallback to another voice')
    source_seconds = mpt_bridge.probe(audio)['seconds']
    if not 20 <= source_seconds <= 26:
        raise ValueError('Unexpected short narrator sample duration')
    source = workspace / 'output' / 'mpt-engine-smoke'
    source.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 38)
    images = []
    for index, (name, color) in enumerate((
        ('KAPI - SADECE TEST KARTI', (27, 38, 46)),
        ('KORIDOR - SADECE TEST KARTI', (48, 31, 41)),
        ('ODA - SADECE TEST KARTI', (29, 43, 36)),
    )):
        image = Image.new('RGB', (1280, 720), color)
        draw = ImageDraw.Draw(image)
        draw.text((90, 280), name, font=font, fill=(240, 235, 225))
        draw.text((90, 360), 'Gorseller gecici; yayin icin kullanilmaz.', font=font, fill=(190, 190, 185))
        target = source / f'placeholder{index}.png'
        image.save(target)
        images.append(str(target.resolve()))
    plan = {'story': SAMPLE, 'narration': str(audio), 'asset_paths': images}
    # MPT is the real renderer for this smoke, not the previous FFmpeg-only test.
    subprocess.run(mpt_bridge.command(plan, upstream), cwd=upstream, check=True)
    outputs = sorted((upstream / 'storage' / 'tasks').rglob('*.mp4'))
    if not outputs:
        raise RuntimeError('MoneyPrinterTurbo produced no MP4 output')
    verified = []
    for path in outputs:
        data = mpt_bridge.probe(path)
        streams = {item.get('codec_type') for item in data.get('streams', [])}
        if {'video', 'audio'} <= streams and abs(data['seconds'] - source_seconds) <= 4:
            verified.append(path)
    if not verified:
        raise RuntimeError('No MPT MP4 with both tracks and matching narrator duration')
    result = {
        'engine': 'MoneyPrinterTurbo',
        'upstream_commit': commit,
        'approved_voice': 'serkan-v6-2-tok',
        'approved_source_audio_sha256': APPROVED_TOK_SHA256,
        'output': str(verified[0].relative_to(workspace)),
        'input_voice_seconds': round(source_seconds, 2),
        'video_seconds': round(mpt_bridge.probe(verified[0])['seconds'], 2),
        'visuals': 'temporary typography cards; story scenes NOT tested or approved',
        'full_length_video_verified': False,
        'youtube_uploaded': False,
    }
    (source / 'smoke_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--audio', type=Path, required=True)
    args = p.parse_args()
    run(args.workspace, args.upstream, args.audio)

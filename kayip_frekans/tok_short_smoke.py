"""Review-only narrator video smoke test; title cards are placeholders, not story visuals."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

APPROVED_SHA = '586244cd639faf5fd5995d1f4a9e74c4bceb7a88852075eee8d046274ea9528b'
SCENES = [
    ('KAPIYI AÇTIĞIMDA', 'Koridorda kimse yoktu.'),
    ('SONRA O SESİ DUYDUM', 'İki yıl önce kaybettiğim kardeşimin sesini…'),
    ('O ZATEN İÇERİDEYDİ', 'KAYIP FREKANS_ • Kısa anlatıcı denemesi'),
]


def produce(audio: Path, target_dir: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    audio = audio.resolve(strict=True)
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    if digest != APPROVED_SHA:
        raise ValueError('Audio does not match the user-approved tok sample; no voice fallback')
    duration = float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=nw=1:nk=1', str(audio)
    ], text=True).strip())
    if not 20 <= duration <= 25:
        raise ValueError('Approved short sample duration unexpectedly changed')
    target_dir.mkdir(parents=True, exist_ok=True)
    bold = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 58)
    regular = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 33)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 23)
    for i, (heading, subtitle) in enumerate(SCENES):
        im = Image.new('RGB', (1280, 720), (12, 17, 27))
        dr = ImageDraw.Draw(im)
        dr.rounded_rectangle((135, 120, 1145, 600), radius=22, outline=(70, 87, 110), width=2)
        dr.line((184, 184, 1096, 184), fill=(94, 105, 124), width=2)
        dr.text((640, 259), heading, font=bold, fill=(232, 236, 244), anchor='mm')
        dr.text((640, 370), subtitle, font=regular, fill=(183, 195, 214), anchor='mm')
        dr.text((640, 545), 'GÖRSELLER TEMSİLİDİR • YAYINLIK DEĞİL', font=small,
                fill=(126, 138, 155), anchor='mm')
        im.save(target_dir / f'card{i}.png')
    sections = [duration * .33, duration * .34, duration * .33]
    playlist = target_dir / 'cards.ffconcat'
    playlist.write_text('ffconcat version 1.0\n' + ''.join(
        f"file '{(target_dir / f'card{i}.png').resolve()}'\nduration {sections[i]:.6f}\n"
        for i in range(3)
    ) + f"file '{(target_dir / 'card2.png').resolve()}'\n", encoding='utf-8')
    mp4 = target_dir / 'KAYIP_FREKANS_TOK_KISA_VIDEO_TEST.mp4'
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-safe', '0',
        '-f', 'concat', '-i', str(playlist), '-i', str(audio), '-map', '0:v:0',
        '-map', '1:a:0', '-vf', 'fps=24,format=yuv420p', '-c:v', 'libx264',
        '-preset', 'veryfast', '-crf', '22', '-c:a', 'aac', '-b:a', '192k',
        '-t', str(duration), '-movflags', '+faststart', str(mp4)
    ], check=True)
    streams = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type',
        '-of', 'json', str(mp4)
    ], text=True))
    if not {'audio', 'video'} <= {s['codec_type'] for s in streams['streams']}:
        raise RuntimeError('Short video lacks video or approved audio track')
    if abs(float(streams['format']['duration']) - duration) > .25:
        raise RuntimeError('Short video and narrator duration mismatch')
    report = {
        'approved_voice': 'serkan-v6-2-tok', 'audio_sha256': digest,
        'duration_seconds': duration, 'video_file': mp4.name,
        'voice_engine_fallback': False, 'moneyprinterturbo_render': False,
        'visuals': 'temporary typography cards; photoreal story scenes NOT tested',
        'uploaded_to_youtube': False, 'full_length_voice_approved': False,
    }
    (target_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return mp4


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('output/tok-short-test'))
    args = parser.parse_args()
    produce(args.audio, args.output)

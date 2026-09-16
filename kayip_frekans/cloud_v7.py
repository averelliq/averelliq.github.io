"""V7: fixes found by inspecting the actual V6 MP4.

- rejects people/models and semantically unrelated Wikimedia photos
- preserves Turkish punctuation in word-timed subtitles
- keeps burned subtitles off the branded intro card (full SRT still contains intro)
- applies darker consistent grading to stock photos
- normalizes final audio to a speech-friendly loudness and 48 kHz stereo
"""
import asyncio
import json
import os
from pathlib import Path
import re
import time
import wave

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

import cloud_v6 as v6
import cloud_v5 as v5
import cloud_v3 as v3

OUT = v3.OUT
BASE_ASSETS = v3.Assets
ORIGINAL_RENDER = v6.cinematic_render

# Broader but more literal Commons searches. The strict semantic filter below
# still has final say; a pretty but unrelated image is rejected.
v5.v4.COMMONS_QUERIES.update({
    'door': 'old wooden door exterior',
    'window': 'old house window exterior',
    'forest': 'dark forest fog trees',
    'house': 'old rural house exterior',
    'corridor': 'empty hallway corridor interior',
    'stairs': 'old staircase interior',
    'room': 'empty old room interior',
    'candle': 'candle dark room',
})

BAD_VISUAL = re.compile(
    r'(?i)\b(person|people|woman|women|man|men|girl|boy|child|children|portrait|model|human|face|'
    r'class\s*room|classroom|school|student|church|chapel|cathedral|monastery|abbey|mosque|temple|'
    r'museum|office|conference|restaurant|hotel|hospital|fresco|painting|statue|sculpture)\b'
)
REQUIRED_VISUAL = {
    'door': re.compile(r'(?i)\b(door|doorway|entrance|gate)\b'),
    'window': re.compile(r'(?i)\b(window|windows|glass)\b'),
    'forest': re.compile(r'(?i)\b(forest|tree|trees|woodland|woods)\b'),
    'house': re.compile(r'(?i)\b(house|home|cottage|cabin|farmhouse|rural|village)\b'),
    'corridor': re.compile(r'(?i)\b(corridor|hallway|passage|cellar|hall)\b'),
    'stairs': re.compile(r'(?i)\b(stair|stairs|staircase|steps)\b'),
    'room': re.compile(r'(?i)\b(room|interior|apartment|living|bedroom|house)\b'),
    'candle': re.compile(r'(?i)\b(candle|flame|wax)\b'),
}


class StrictCinematicAssets(BASE_ASSETS):
    """Reject visual mismatch even if the provider returned a technically valid file."""
    def _remove_last_record(self):
        if self.used:
            self.used.pop()
            v3.save('visual_sources.json', self.used)

    def get(self, key):
        errors = []
        for _ in range(8):
            try:
                path = super().get(key)
            except Exception as exc:
                errors.append(str(exc)); break
            record = self.used[-1] if self.used else {}
            if record.get('provider') == 'Generated':
                # Let V6 try adjacent REAL categories first. Only its final fallback may
                # deliberately choose an original drawing if every external source failed.
                self._remove_last_record()
                raise ValueError(f'{key}: gerçek fotoğraf bulunamadı')
            alt = (record.get('alt') or '').strip()
            required = REQUIRED_VISUAL.get(key)
            if BAD_VISUAL.search(alt) or (required and not required.search(alt)):
                errors.append(f'uygunsuz görsel: {alt[:80]}')
                self._remove_last_record()
                continue
            return path
        raise ValueError(f'{key} için hikâyeyle uyumlu insansız görsel bulunamadı: ' + '; '.join(errors[-2:]))


def cinematic_frame(path, index):
    """Unified dark grading; never adds or invents people/objects."""
    image = ImageOps.fit(Image.open(path).convert('RGB'), (v3.W, v3.H), method=Image.Resampling.LANCZOS)
    image = ImageEnhance.Color(image).enhance(.48)
    image = ImageEnhance.Contrast(image).enhance(1.20)
    image = ImageEnhance.Brightness(image).enhance(.60)
    overlay = Image.new('RGBA', (v3.W, v3.H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Darker edges and a bottom readability gradient, without an opaque subtitle box.
    for n, alpha in ((0, 72), (42, 52), (84, 34), (126, 18)):
        draw.rectangle((n, n, v3.W-n-1, v3.H-n-1), outline=(0, 0, 0, alpha), width=42)
    for y in range(int(v3.H*.64), v3.H):
        alpha = int(115 * (y-v3.H*.64)/(v3.H*.36))
        draw.line((0, y, v3.W, y), fill=(0, 0, 0, alpha))
    image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    result = OUT / f'shot-{index:04}.jpg'
    image.save(result, quality=95)
    return result


def _norm_word(value):
    return re.sub(r'[^a-z0-9çğıöşüâîû]+', '', value.casefold())


def _display_words(text, boundaries):
    """Map Edge word timings back to original tokens so punctuation/quotes survive."""
    original = text.split()
    mapped, cursor = [], 0
    for boundary in boundaries:
        target = _norm_word(boundary.get('text', ''))
        chosen = boundary.get('text', '')
        for j in range(cursor, min(len(original), cursor + 5)):
            candidate = original[j]
            c = _norm_word(candidate)
            if target and (c == target or c.startswith(target) or target.startswith(c)):
                chosen = candidate
                cursor = j + 1
                break
        mapped.append(chosen)
    return mapped


async def tts_v7(text, path):
    import edge_tts
    boundaries = []
    # Slightly slower/deeper than default, but modest enough to avoid obvious pitch artifacts.
    with path.open('wb') as handle:
        async for chunk in edge_tts.Communicate(
            text, v3.VOICE, rate='-8%', pitch='-3Hz', boundary='WordBoundary'
        ).stream():
            if chunk['type'] == 'audio':
                handle.write(chunk['data'])
            elif chunk['type'] == 'WordBoundary':
                boundaries.append(chunk)
    if not boundaries:
        raise ValueError('Kelime zamanları gelmedi; yaklaşık altyazıya geçilmedi.')
    return boundaries


def caption_cues_v7(boundaries, offset, source_text):
    displays = _display_words(source_text, boundaries)
    cues, group = [], []
    for boundary, display in zip(boundaries, displays):
        prospective = ' '.join([x[1] for x in group] + [display])
        elapsed = 0 if not group else (boundary['offset'] - group[0][0]['offset']) / 1e7
        # Shorter captions: usually one line, never the giant 3-line blocks seen in V6.
        if group and (len(prospective) > 39 or elapsed > 3.25):
            a = offset + group[0][0]['offset'] / 1e7
            b = offset + (group[-1][0]['offset'] + group[-1][0]['duration']) / 1e7
            cues.append((a, b, ' '.join(x[1] for x in group)))
            group = []
        group.append((boundary, display))
    if group:
        a = offset + group[0][0]['offset'] / 1e7
        b = offset + (group[-1][0]['offset'] + group[-1][0]['duration']) / 1e7
        cues.append((a, b, ' '.join(x[1] for x in group)))
    return cues


def narrate_v7(parts):
    frames, cues, segments = [], [], []
    total = 0.0
    passages = []
    for part in parts:
        paragraphs = [p.strip() for p in part.split('\n') if p.strip()]
        for paragraph in paragraphs:
            group = []
            for sentence in v3.bot.sentences(paragraph):
                group.append(sentence)
                if len(' '.join(group)) >= 650:
                    passages.append(' '.join(group)); group = []
            if group:
                passages.append(' '.join(group))
    for i, text in enumerate(passages):
        mp3 = OUT / f'narration-{i:03}.mp3'
        for attempt in range(3):
            try:
                boundaries = asyncio.run(tts_v7(text, mp3)); break
            except Exception:
                if attempt == 2: raise
                time.sleep(2 ** attempt)
        wav = OUT / f'narration-{i:03}.wav'
        v3.bot.run('ffmpeg', '-v', 'error', '-y', '-i', mp3, '-ac', '1', '-ar', '24000', wav)
        with wave.open(str(wav), 'rb') as reader:
            audio = reader.readframes(reader.getnframes())
            duration = reader.getnframes() / reader.getframerate()
        frames.append(audio)
        cues.extend(caption_cues_v7(boundaries, total, text))
        segments.append({'start': total, 'end': total+duration, 'text': text, 'kind': v3.category(text)})
        total += duration
        print(f'Ses {i+1}/{len(passages)}', flush=True)
    with wave.open(str(OUT/'narration.wav'), 'wb') as writer:
        writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(24000)
        writer.writeframes(b''.join(frames))
    v3.save('captions.srt', '\n\n'.join(
        f'{i+1}\n{v3.bot.stamp(a)} --> {v3.bot.stamp(b)}\n{text}'
        for i, (a, b, text) in enumerate(cues)
    ) + '\n')
    v3.save('scene_plan.json', segments)
    return total, segments, cues


def _time_seconds(stamp):
    h, m, rest = stamp.replace(',', '.').split(':')
    return int(h)*3600 + int(m)*60 + float(rest)


def story_only_srt(full_srt, story_start):
    """Keep full external captions, but burn only story captions over the MP4."""
    kept = []
    for block in re.split(r'\n\s*\n', full_srt.strip()):
        lines = block.splitlines()
        if len(lines) < 3 or '-->' not in lines[1]:
            continue
        start = _time_seconds(lines[1].split('-->')[0].strip())
        if start >= story_start - .08:
            kept.append(lines[1:])
    return '\n\n'.join(f'{i+1}\n' + '\n'.join(lines) for i, lines in enumerate(kept)) + '\n'


def render_v7(title, total, segments, report):
    captions_path = OUT/'captions.srt'
    full_captions = captions_path.read_text(encoding='utf-8')
    story_start = segments[1]['start'] if len(segments) > 1 else 0
    burn = story_only_srt(full_captions, story_start)
    v3.save('captions_burned.srt', burn)
    # V6 renderer expects captions.srt. Temporarily substitute the story-only burn file,
    # then restore the complete SRT for download/YouTube accessibility.
    captions_path.write_text(burn, encoding='utf-8')
    try:
        ORIGINAL_RENDER(title, total, segments, report)
    finally:
        captions_path.write_text(full_captions, encoding='utf-8')

    # Normalize after the visual render. Video is stream-copied, so no second image quality loss.
    normalized = OUT/'final-normalized.mp4'
    v3.bot.run(
        'ffmpeg', '-v', 'error', '-y', '-i', OUT/'final.mp4',
        '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'copy',
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7', '-ar', '48000', '-ac', '2',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', normalized
    )
    os.replace(normalized, OUT/'final.mp4')
    probe = json.loads(__import__('subprocess').check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(OUT/'final.mp4')
    ]))
    streams = {s['codec_type']: s for s in probe['streams']}
    if streams['audio'].get('sample_rate') != '48000' or int(streams['audio'].get('channels', 0)) != 2:
        raise ValueError('Final ses 48 kHz stereo normalizasyondan geçmedi.')
    current = json.loads((OUT/'quality_report.json').read_text(encoding='utf-8'))
    current.update({
        'version': 7,
        'intro_captions_burned': False,
        'external_srt_contains_intro': True,
        'caption_punctuation_preserved': True,
        'people_in_stock_images_allowed': False,
        'audio_target_lufs': -16,
        'audio_true_peak_target_db': -1.5,
        'audio_sample_rate': 48000,
        'audio_channels': 2,
    })
    v3.save('quality_report.json', current); v3.save('validation.json', current)
    metadata = json.loads((OUT/'metadata.json').read_text(encoding='utf-8'))
    metadata['audio'] = 'AAC 48 kHz stereo; loudness normalized toward -16 LUFS / -1.5 dBTP'
    v3.save('metadata.json', metadata)


# Install V7 overrides after V4/V5/V6 have installed their own wrappers.
v3.Assets = StrictCinematicAssets
v3.framed_photo = cinematic_frame
v3.narrate = narrate_v7
v3.render = render_v7

if __name__ == '__main__':
    v3.main()

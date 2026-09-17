"""V13: user-selected Serkan voice, genuine channel logo, and guarded story visuals.

The user's reference MP3 is not uploaded to this public repo and is not cloned.
All new dialogue is generated through the selected licensed ElevenLabs voice ID.
No silent fallback to Edge or to another 'deep' voice.
"""
import io
import json
import os
from pathlib import Path
import re
import wave

from PIL import Image, ImageDraw, ImageFont, ImageOps

import cloud_v12 as v12
import cloud_v11 as v11
import cloud_v9 as v9
import cloud_v8 as v8
import cloud_v7 as v7
import cloud_v6 as v6
import cloud_v3 as v3
import serkan_voice as voice
import brand_logo

OUT = v3.OUT
BLOCKED_UNRELATED = re.compile(
    r'(?i)\b(airplane|airport|swimming pool|shopping mall|sports stadium|car showroom|'
    r'fashion show|motorcycle|luxury villa|office building|skyscraper|railway station)\b'
)


class StoryContextAssets(v12.StoryContextAssets):
    def get(self, key):
        errors = []
        for _ in range(8):
            source = super().get(key)
            record = self.used[-1] if self.used else {}
            if record.get('provider') != 'Generated' and BLOCKED_UNRELATED.search(record.get('alt') or ''):
                errors.append('konu dışı modern nesne/mekân')
                self._drop_last()
                continue
            return source
        raise ValueError(f'{key} için uygun bağlam görseli yok: ' + '; '.join(errors))


def _passages(parts):
    """Treat the opening as one distinct segment so the intro graphic stays in sync."""
    if not parts or not parts[0].strip():
        raise ValueError('Giriş metni yok.')
    result = [parts[0].strip()]
    for part in parts[1:]:
        for paragraph in (p.strip() for p in part.split('\n')):
            if not paragraph:
                continue
            group = []
            for sentence in v3.bot.sentences(paragraph):
                group.append(sentence)
                if len(' '.join(group)) >= 500:
                    result.append(' '.join(group)); group = []
            if group:
                result.append(' '.join(group))
    return result


def narrate_serkan(parts):
    """Produce authentic Serkan audio and actual character-aligned captions."""
    voice.require_key()  # Fail early; never generate fallback voice.
    passages = _passages(parts)
    segments, cues, frames = [], [], []
    total = 0.0
    for index, text in enumerate(passages):
        previous = passages[index - 1] if index else ''
        upcoming = passages[index + 1] if index + 1 < len(passages) else ''
        mp3_bytes, words = voice.synthesize(text, previous_text=previous, next_text=upcoming)
        mp3 = OUT / f'narration-{index:03}.mp3'
        mp3.write_bytes(mp3_bytes)
        wav = OUT / f'narration-{index:03}.wav'
        v3.bot.run('ffmpeg', '-v', 'error', '-y', '-i', mp3,
                   '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', wav)
        with wave.open(str(wav), 'rb') as reader:
            duration = reader.getnframes() / reader.getframerate()
            frames.append(reader.readframes(reader.getnframes()))
        last_word = max((w['offset'] + w['duration']) / 10_000_000 for w in words)
        if last_word > duration + .20 or duration <= 0:
            raise ValueError('Serkan ses uzunluğu ile kelime zamanları uyuşmuyor.')
        cues.extend(v11.compact_caption_cues(words, total, text))
        segments.append({'start': total, 'end': total + duration, 'text': text,
                         'kind': v3.category(text)})
        total += duration
        print(f'Serkan sesi {index + 1}/{len(passages)}', flush=True)
    with wave.open(str(OUT / 'narration.wav'), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(24000)
        writer.writeframes(b''.join(frames))
    v3.save('captions.srt', '\n\n'.join(
        f'{i+1}\n{v3.bot.stamp(a)} --> {v3.bot.stamp(b)}\n{content}'
        for i, (a, b, content) in enumerate(cues)
    ) + '\n')
    v3.save('scene_plan.json', segments)
    v3.save('voice_report.json', {
        'voice_provider': 'ElevenLabs', 'voice_name': 'Serkan Demirci - Deep, Soft and Balanced',
        'voice_id': voice.VOICE_ID, 'voice_model': voice.MODEL_ID,
        'caption_timing': 'ElevenLabs source-character timestamps',
        'voice_fallback_used': False, 'sample_voice_cloned': False,
    })
    return total, segments, cues


def make_brand_intro(title):
    """Use the user's original emblem, embedded as a compact PNG, not a generic text card."""
    W, H = v3.W, v3.H
    im = Image.new('RGB', (W, H), (5, 6, 9))
    draw = ImageDraw.Draw(im, 'RGBA')
    cx, cy = W // 2, 375
    for radius, alpha, width in ((350, 48, 4), (290, 80, 3), (245, 70, 2)):
        draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),
                     outline=(206, 25, 35, alpha), width=width)
    logo = Image.open(io.BytesIO(brand_logo.logo_png())).convert('RGB')
    logo = ImageOps.fit(logo, (490, 490), method=Image.Resampling.LANCZOS)
    im.paste(logo, (cx-245, cy-245))
    draw = ImageDraw.Draw(im, 'RGBA')
    draw.line((500, 675, 1420, 675), fill=(190, 30, 39, 205), width=3)
    font = ImageFont.truetype(v3.bot.FONT, 62)
    subtitle = ImageFont.truetype(v3.bot.FONT, 34)
    headline = title[:55]
    width = draw.textbbox((0, 0), headline, font=font)[2]
    draw.text(((W-width)//2, 713), headline, font=font,
              fill=(230, 224, 222, 255), stroke_width=2, stroke_fill=(5, 5, 5, 255))
    tagline = 'KAYIP FREKANS_  •  KORKU HİKÂYELERİ'
    width = draw.textbbox((0, 0), tagline, font=subtitle)[2]
    draw.text(((W-width)//2, 836), tagline, font=subtitle, fill=(172, 172, 177, 245))
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / 'intro-card.jpg'
    im.save(dest, quality=95)
    return dest


def render_v13(title, total, segments, report):
    v12.render_v12(title, total, segments, report)
    info = json.loads((OUT / 'voice_report.json').read_text(encoding='utf-8'))
    current = json.loads((OUT / 'quality_report.json').read_text(encoding='utf-8'))
    current.update(info)
    current.update({'version': 13, 'intro_channel_logo_used': True,
                    'intro_palette': 'black-red-offwhite',
                    'extra_unrelated_visual_filter': True,
                    'human_review_required': True, 'youtube_uploaded': False})
    v3.save('quality_report.json', current)
    v3.save('validation.json', current)
    metadata = json.loads((OUT / 'metadata.json').read_text(encoding='utf-8'))
    metadata.update({'narrator': 'Serkan Demirci (ElevenLabs)',
                     'narrator_voice_id': voice.VOICE_ID,
                     'narrator_sample_cloned': False})
    v3.save('metadata.json', metadata)


# These are the live V3 callbacks used by the staged GitHub workflow.
v8.DiverseAssets = StoryContextAssets
v3.Assets = StoryContextAssets
v6.make_intro_frame = make_brand_intro
v3.narrate = narrate_serkan
v3.render = render_v13

if __name__ == '__main__':
    v3.main()

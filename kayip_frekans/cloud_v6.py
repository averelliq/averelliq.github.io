"""V6: review-driven cinematic renderer for KAYIP FREKANS_.

Keeps V5 story/Turkish quality gates, but fixes the visual problems found in
real outputs: one category dominating the whole video, long slideshow shots,
intro art bleeding into the story, tiny subtitles and fragile source-diversity
checks. The renderer remains CPU-only and never uploads to YouTube.
"""
import json
import math
import os
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

import cloud_v5 as v5  # imports V4/V5 quality + resilient asset monkey patches
import cloud_v3 as v3

W, H, FPS = v3.W, v3.H, v3.FPS
OUT = v3.OUT

KEYWORDS = {
    'window': ('pencere', 'perde', 'cam', 'rüzgâr', 'rüzgar'),
    'stairs': ('merdiven', 'basamak', 'bodrum'),
    'forest': ('orman', 'ağaç', 'patika', 'çalılık'),
    'candle': ('mum', 'kandil', 'alev'),
    'corridor': ('koridor', 'hol', 'antre', 'adım sesi', 'yürüdüm'),
    'room': ('salon', 'oda', 'duvar', 'masa', 'telefon', 'sıva', 'yatak'),
    'house': ('köy', 'ev', 'bahçe', 'avlu', 'dışarı', 'sabah'),
    'door': ('kapı', 'kilit', 'tokmak', 'eşik'),
}

ALTERNATES = {
    'door': ['door', 'room', 'corridor', 'window', 'house'],
    'room': ['room', 'corridor', 'window', 'door', 'house'],
    'corridor': ['corridor', 'room', 'door', 'stairs', 'window'],
    'window': ['window', 'room', 'house', 'corridor', 'door'],
    'house': ['house', 'door', 'window', 'room', 'corridor'],
    'stairs': ['stairs', 'corridor', 'room', 'door', 'candle'],
    'forest': ['forest', 'house', 'door', 'window', 'corridor'],
    'candle': ['candle', 'room', 'corridor', 'door', 'window'],
}


def rich_category(text, fallback='corridor'):
    """Choose a visual subject from the local sentence, not the whole paragraph."""
    low = text.casefold()
    scores = {key: sum(low.count(term) for term in terms) for key, terms in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else fallback


def choose_visual_kinds(text, count, fallback='corridor'):
    """Produce shot subjects from sentence-level context while avoiding monotony."""
    sentences = v3.bot.sentences(text) or [text]
    local = [rich_category(s, fallback) for s in sentences]
    result = []
    for i in range(count):
        pos = min(len(local) - 1, int(i * len(local) / max(1, count)))
        primary = local[pos]
        choices = ALTERNATES.get(primary, [primary, 'room', 'corridor', 'door', 'window'])
        # Preserve the actual subject most of the time, but prevent one noun such as
        # "kapı" from forcing every shot in a two-minute sequence to be identical.
        candidate = choices[0] if i % 3 != 2 else choices[(i // 3 + 1) % len(choices)]
        if result and candidate == result[-1] and len(choices) > 1:
            candidate = choices[1]
        result.append(candidate)
    return result


def make_intro_frame(title):
    """Dedicated intro frame: it can never spill into a story shot."""
    source = v3.bot.backdrop('karanlık koridor', 8800)
    image = ImageOps.fit(Image.open(source).convert('RGB'), (W, H), method=Image.Resampling.LANCZOS)
    image = ImageEnhance.Brightness(image).enhance(.48)
    image = ImageEnhance.Contrast(image).enhance(1.18)
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.rounded_rectangle((120, 220, 1800, 835), radius=34,
                           fill=(4, 7, 12, 205), outline=(150, 78, 94, 235), width=4)
    draw.line((190, 370, 1730, 370), fill=(150, 78, 94, 230), width=3)
    draw.text((195, 270), 'KAYIP FREKANS_', font=ImageFont.truetype(v3.bot.FONT, 98),
              fill=(246, 240, 231, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    short = title[:52]
    draw.text((200, 455), short, font=ImageFont.truetype(v3.bot.FONT, 56),
              fill=(221, 207, 204, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    draw.text((202, 605), 'Beğenip abone olursanız çok sevinirim.',
              font=ImageFont.truetype(v3.bot.FONT, 35), fill=(188, 169, 171, 255))
    draw.text((202, 682), 'Şimdi hikâyemize geçelim…',
              font=ImageFont.truetype(v3.bot.FONT, 35), fill=(188, 169, 171, 255))
    path = OUT / 'intro-card.jpg'
    image.save(path, quality=95)
    return path


def _asset_with_retry(assets, kind, recent):
    """Prefer a different licensed image; if impossible, use a distinct safe fallback."""
    order = ALTERNATES.get(kind, [kind, 'room', 'corridor', 'door', 'window'])
    last_error = None
    for candidate in order[:3]:
        try:
            source = assets.get(candidate)
            if source.name not in recent[-2:]:
                return source, candidate
        except Exception as exc:
            last_error = exc
    # ResilientAssets supplies a unique original drawing. This is intentionally
    # preferred over reusing the exact same photograph for many consecutive shots.
    if hasattr(assets, '_procedural_get'):
        return assets._procedural_get(kind), kind
    if last_error:
        raise last_error
    return assets.get(kind), kind


def _render_still(photo, index, seconds):
    frames = max(1, round(seconds * FPS))
    clip = OUT / f'v-{index:04}.mp4'
    # Alternating slow push/pull plus tiny horizontal drift removes the static-slide feel.
    if index % 2 == 0:
        zoom = "min(1.095,1+on*0.00016)"
        x = "iw/2-iw/zoom/2+8*sin(on/28)"
    else:
        zoom = "max(1.0,1.095-on*0.00016)"
        x = "iw/2-iw/zoom/2-8*sin(on/31)"
    vf = (f"scale=2400:1350,zoompan=z='{zoom}':x='{x}':y='ih/2-ih/zoom/2':"
          f"d={frames}:s={W}x{H}:fps={FPS},format=yuv420p")
    v3.bot.run('ffmpeg', '-v', 'error', '-y', '-i', photo, '-vf', vf,
               '-frames:v', frames, '-an', '-c:v', 'libx264', '-preset', 'veryfast',
               '-crf', '20', clip)
    return clip, frames / FPS


def cinematic_render(title, total, segments, report):
    assets = v3.Assets()
    shots, recent = [], []
    timeline = 0.0
    index = 0
    intro_shots = 0

    for seg_index, seg in enumerate(segments):
        duration = seg['end'] - seg['start']
        is_intro = seg_index == 0 and 'merhaba kayıp frekans' in seg['text'].casefold()
        # 7–9 seconds per shot: substantially more movement than the old 12-second slides.
        target = 8.0 if not is_intro else 7.5
        count = max(1, math.ceil(duration / target))
        kinds = choose_visual_kinds(seg['text'], count, seg.get('kind', 'corridor'))
        per_shot = duration / count

        if is_intro:
            intro = make_intro_frame(title)
            for _ in range(count):
                clip, actual = _render_still(intro, index, per_shot)
                shots.append({'path': clip.name, 'source': intro.name, 'start': timeline,
                              'duration': actual, 'category': 'intro', 'intro': True})
                timeline += actual; index += 1; intro_shots += 1
            continue

        for kind in kinds:
            source, used_kind = _asset_with_retry(assets, kind, recent)
            recent.append(source.name)
            photo = v3.framed_photo(source, index)
            clip, actual = _render_still(photo, index, per_shot)
            shots.append({'path': clip.name, 'source': source.name, 'start': timeline,
                          'duration': actual, 'category': used_kind, 'intro': False})
            timeline += actual; index += 1

    story_shots = [s for s in shots if not s['intro']]
    min_story_shots = 6 if report.get('preview') else max(12, round(total / 12))
    if len(story_shots) < min_story_shots:
        raise ValueError(f'Hikâye sahnesi yetersiz: {len(story_shots)} < {min_story_shots}.')
    unique_story_sources = {s['source'] for s in story_shots}
    unique_categories = {s['category'] for s in story_shots}
    required_sources = 2 if report.get('preview') else min(5, max(3, len(story_shots)//6))
    if len(unique_story_sources) < required_sources:
        raise ValueError(f'Gerçek görsel çeşitliliği yetersiz: {len(unique_story_sources)} < {required_sources}.')
    if len(unique_categories) < 2:
        raise ValueError('Sahne planı tek görsel kategoriye sıkıştı.')

    v3.save('shots.json', shots)
    v3.save('concat.txt', ''.join(f"file '{s['path']}'\n" for s in shots))
    v3.bot.run('ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0',
               '-i', OUT/'concat.txt', '-c', 'copy', OUT/'visuals.mp4')

    # Original ambience only: low drone + quiet filtered brown noise. Both are ducked
    # under speech, so the narration remains intelligible and there are no copyright assets.
    drone = f"aevalsrc=0.020*sin(2*PI*55*t)+0.008*sin(2*PI*82.41*t):s=24000:d={total}"
    filters = (
        "[0:v]tpad=stop_mode=clone:stop_duration=1,"
        "subtitles=output/captions.srt:force_style='FontName=DejaVu Sans,FontSize=46,"
        "Outline=3,Shadow=1,MarginV=58,Alignment=2'[v];"
        "[1:a]highpass=f=65,lowpass=f=11500,alimiter=limit=0.90:level=false,asplit=2[voice][side];"
        "[2:a]afade=t=in:d=2,volume=0.55[drone];"
        "[3:a]highpass=f=70,lowpass=f=950,volume=0.010[wind];"
        "[drone][wind]amix=inputs=2:duration=longest:normalize=0[amb];"
        "[amb][side]sidechaincompress=threshold=0.012:ratio=8:attack=15:release=550[bed];"
        "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]"
    )
    v3.bot.run('ffmpeg', '-v', 'error', '-y', '-i', OUT/'visuals.mp4',
               '-i', OUT/'narration.wav', '-f', 'lavfi', '-i', drone,
               '-f', 'lavfi', '-i', f'anoisesrc=color=brown:amplitude=0.12:sample_rate=24000:d={total}',
               '-filter_complex', filters, '-map', '[v]', '-map', '[a]', '-t', f'{total:.5f}',
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT/'final.mp4')

    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(OUT/'final.mp4')
    ]))
    measured = float(probe['format']['duration'])
    streams = {s['codec_type']: s for s in probe['streams']}
    if abs(measured-total) > .20 or set(streams) != {'video', 'audio'}:
        raise ValueError('Final ses/görüntü doğrulaması başarısız.')
    if int(streams['video'].get('width', 0)) != W or int(streams['video'].get('height', 0)) != H:
        raise ValueError('Final video 1920x1080 değil.')

    # Thumbnail must use the STORY, never the intro/subscribe card.
    first_story_index = intro_shots
    cover_path = OUT / f'shot-{first_story_index:04}.jpg'
    if not cover_path.exists():
        raise ValueError('Kapak için ilk hikâye karesi bulunamadı.')
    cover = Image.open(cover_path).convert('RGB')
    draw = ImageDraw.Draw(cover)
    thumb = 'KAPININ ARDINDA\nKİM VAR?' if report.get('preview') else title[:58]
    y = 650
    for line in thumb.split('\n'):
        draw.text((105, y), line, font=ImageFont.truetype(v3.bot.FONT, 94), fill='white',
                  stroke_width=6, stroke_fill='black')
        y += 120
    cover.save(OUT/'thumbnail.jpg', quality=95)

    sources_path = OUT/'visual_sources.json'
    sources = json.loads(sources_path.read_text(encoding='utf-8')) if sources_path.exists() else []
    unique_records = {str(p.get('id')): p for p in sources}.values()
    providers, credit_lines = set(), []
    for p in unique_records:
        provider = p.get('provider', 'Pexels'); providers.add(provider)
        if provider == 'Generated':
            credit_lines.append('KAYIP FREKANS_ / özgün programatik atmosfer çizimi')
        else:
            line = f"{p.get('photographer','Bilinmeyen')} / {provider} / {p.get('license','')}"
            if p.get('url'): line += f" / {p['url']}"
            credit_lines.append(line)
    credits = '\n'.join(credit_lines)
    v3.save('credits.txt', credits)
    v3.save('metadata.json', {
        'title': title, 'channel': 'KAYIP FREKANS_', 'duration_seconds': measured,
        'test_video': bool(report.get('preview')),
        'description': f'{title}\n\nKurmaca cinli korku hikâyesi. Yapay zekâ destekli seslendirme. '
                       'Atmosfer görüntüleri temsili görsellerdir.\n\nGörsel kaynakları:\n' + credits,
        'tags': ['korku hikayeleri', 'cinli hikayeler', 'KAYIP FREKANS_'],
        'visual_providers': sorted(providers),
    })
    avg = sum(s['duration'] for s in story_shots) / max(1, len(story_shots))
    report.update({
        'version': 6, 'mechanical_checks_passed': True, 'duration_seconds': measured,
        'shots': len(shots), 'story_shots': len(story_shots), 'intro_shots': intro_shots,
        'unique_story_sources': len(unique_story_sources),
        'visual_categories': sorted(unique_categories), 'average_story_shot_seconds': round(avg, 2),
        'resolution': '1920x1080', 'subtitle_alignment': 'TTS word boundaries',
        'subtitle_font_size': 46, 'visual_providers': sorted(providers),
        'human_review_required': True, 'youtube_uploaded': False,
    })
    v3.save('quality_report.json', report); v3.save('validation.json', report)
    summary = os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        Path(summary).write_text(
            f'## KAYIP FREKANS V6\n{measured:.1f} saniye; {len(story_shots)} hikâye planı; '
            f'{len(unique_story_sources)} farklı kaynak; ortalama plan {avg:.1f}s. '
            '1080p, kelime zamanlı altyazı. YouTube yüklenmedi.\n', encoding='utf-8')


# V5 has already installed strict story checks and resilient assets on v3.
v3.render = cinematic_render

if __name__ == '__main__':
    v3.main()

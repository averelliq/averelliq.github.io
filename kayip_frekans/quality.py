"""Small, dependency-free editorial checks for KAYIP FREKANS_ videos.

These are mechanical checks, not a substitute for watching the finished video.
"""
import json
from pathlib import Path
import re

CHANNEL = 'KAYIP FREKANS_'
INTRO_OPEN = 'Merhaba Kayıp Frekans dinleyicileri.'
INTRO_CTA = 'Videoyu beğenip kanalımıza abone olursanız çok sevinirim.'
INTRO_END = 'Şimdi hikâyemize geçelim.'


def clean_title(title):
    title = re.sub(r'\s*[—–-]\s*Üretim Testi\s*$', '', str(title), flags=re.I)
    title = re.sub(r'(?i)\bfinal story\b', '', title)
    title = re.sub(r'\s+', ' ', title).strip(' .:—–-"“”')
    if not title:
        raise ValueError('Hikâye başlığı boş.')
    return title[:95]


def intro_text(title):
    title = clean_title(title)
    return (f'{INTRO_OPEN} Bugünkü hikâyemizin adı: {title}. '
            f'{INTRO_CTA} {INTRO_END}')


# TTS should read clock times in natural Turkish rather than English digits.
_HOURS = ('on iki', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi',
          'sekiz', 'dokuz', 'on', 'on bir')
_MINUTES = ('sıfır', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz',
            'dokuz', 'on', 'on bir', 'on iki', 'on üç', 'on dört', 'on beş',
            'on altı', 'on yedi', 'on sekiz', 'on dokuz', 'yirmi',
            'yirmi bir', 'yirmi iki', 'yirmi üç', 'yirmi dört', 'yirmi beş',
            'yirmi altı', 'yirmi yedi', 'yirmi sekiz', 'yirmi dokuz',
            'otuz', 'otuz bir', 'otuz iki', 'otuz üç', 'otuz dört',
            'otuz beş', 'otuz altı', 'otuz yedi', 'otuz sekiz', 'otuz dokuz',
            'kırk', 'kırk bir', 'kırk iki', 'kırk üç', 'kırk dört',
            'kırk beş', 'kırk altı', 'kırk yedi', 'kırk sekiz', 'kırk dokuz',
            'elli', 'elli bir', 'elli iki', 'elli üç', 'elli dört',
            'elli beş', 'elli altı', 'elli yedi', 'elli sekiz', 'elli dokuz')


def spoken_clock(match):
    hour, minute = (int(match.group(1)), int(match.group(2)))
    if hour > 23 or minute > 59:
        return match.group(0)
    period = 'gece' if hour < 6 or hour >= 22 else ('sabah' if hour < 12 else ('öğleden sonra' if hour < 18 else 'akşam'))
    number = _HOURS[hour % 12]
    if minute == 0:
        return f'{period} {number}'
    if minute == 30:
        return f'{period} {number} buçuk'
    return f'{period} {number} {_MINUTES[minute]}'


def normalize_for_speech(text):
    return re.sub(r'(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)', spoken_clock, text)


def validate_story(title, parts, minutes, smoke=False):
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError('Hikâye bölümleri bulunamadı.')
    clean_title(title)
    normalized = [normalize_for_speech(str(p).strip()) for p in parts]
    if any(not p for p in normalized):
        raise ValueError('Boş hikâye bölümü var.')
    text = '\n\n'.join(normalized)
    words = len(text.split())
    if words < (25 if smoke else int(minutes * 120 * 0.60)):
        raise ValueError(f'Hikâye çok kısa: {words} kelime, hedef yaklaşık {minutes} dakika. Video üretilmedi.')
    if re.search(r'(?i)\bfinal story\b', text):
        raise ValueError('Hikâyede yanlışlıkla Final Story ifadesi kaldı.')
    if len(set(p.strip() for p in normalized)) != len(normalized):
        raise ValueError('Tekrarlanan hikâye bölümleri bulundu.')
    if not re.search(r'[.!?…][\s”"\']*$', text):
        raise ValueError('Hikâye bitişinde noktalama eksik; yarım kalmış olabilir.')
    return normalized, {'story_words': words, 'target_minutes': minutes,
                        'estimated_story_minutes_at_120_wpm': round(words / 120, 1),
                        'chapters': len(normalized), 'mechanical_checks_passed': True,
                        'human_review_required': True}


def write_quality_report(output_dir, report, video_seconds=None):
    result = dict(report)
    if video_seconds is not None:
        result['measured_video_seconds'] = round(float(video_seconds), 2)
        result['measured_video_minutes'] = round(float(video_seconds) / 60, 2)
    result['visual_style'] = 'procedural illustrations; NOT photorealistic AI video'
    result['subtitle_accuracy'] = 'approximately aligned within spoken sentences'
    result['youtube_uploaded'] = False
    result['human_review_required'] = True
    Path(output_dir, 'quality_report.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result

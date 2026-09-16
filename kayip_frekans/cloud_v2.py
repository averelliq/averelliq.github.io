"""Cloud v2 entrypoint. Preserves the proven CPU renderer and its no-upload policy."""
import json
from pathlib import Path
import re

import bot
from quality import clean_title, intro_text, validate_story, write_quality_report

ORIGINAL_STORY = bot.story
ORIGINAL_BACKDROP = bot.backdrop


def improved_story(topic, minutes, smoke):
    title, parts = ORIGINAL_STORY(topic, minutes, smoke)
    normalized, report = validate_story(title, parts, minutes, smoke)
    clean = clean_title(title)
    bot.OUT.mkdir(exist_ok=True)
    (bot.OUT / 'story_only.txt').write_text('\n\n'.join(normalized), encoding='utf-8')
    (bot.OUT / 'intro.txt').write_text(intro_text(clean), encoding='utf-8')
    write_quality_report(bot.OUT, report)
    # A separate intro passage is spoken by the SAME voice as the story.
    # The renderer composes this before the first incident, never as metadata only.
    return title, [intro_text(clean)] + normalized


def improved_backdrop(text, number):
    """More scene-specific drawn frames. These are illustrations, not AI photographs."""
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance

    path = ORIGINAL_BACKDROP(text, number)
    image = Image.open(path).convert('RGB')
    draw = ImageDraw.Draw(image)
    low = text.casefold()
    if number == 0 and 'merhaba kayıp frekans' in low:
        # The mandatory narrated opening gets a recognizable, original title card.
        draw.rectangle((120, 176, 1160, 552), fill=(9, 12, 18), outline=(116, 72, 81), width=3)
        draw.line((165, 235, 1115, 235), fill=(110, 66, 79), width=3)
        draw.text((175, 275), 'KAYIP FREKANS_',
                  font=ImageFont.truetype(bot.FONT, 65), fill=(235, 230, 221))
        draw.text((182, 388), 'GERCEK OLMAYAN BIR SES. GERCEK BIR KORKU.',
                  font=ImageFont.truetype(bot.FONT, 24), fill=(169, 145, 148))
    elif any(k in low for k in ('bodrum', 'merdiven', 'basamak')):
        draw.polygon([(320, 715), (1000, 715), (740, 315), (550, 315)], fill=(14, 18, 24))
        for y in range(415, 710, 65):
            inset = (y - 330) // 3
            draw.line((555 - inset, y, 735 + inset, y), fill=(77, 82, 83), width=5)
        draw.rectangle((560, 175, 722, 318), fill=(3, 5, 9))
    elif any(k in low for k in ('hastane', 'hasta odası', 'sedye')):
        draw.rectangle((320, 415, 970, 495), fill=(91, 104, 100))
        draw.rectangle((380, 375, 720, 438), fill=(165, 166, 151))
        draw.line((360, 490, 360, 605), fill=(121, 137, 135), width=12)
        draw.line((950, 490, 950, 605), fill=(121, 137, 135), width=12)
    elif any(k in low for k in ('yatak', 'uyandım', 'uyuyordum', 'odamda')):
        draw.rectangle((275, 435, 1015, 565), fill=(40, 48, 54))
        draw.rectangle((320, 385, 610, 465), fill=(135, 137, 136))
        draw.line((250, 564, 1040, 564), fill=(90, 78, 67), width=15)
    # A very slight contrast adjustment, keeping the renderer inexpensive on CPU.
    image = ImageEnhance.Contrast(image).enhance(1.10)
    image.save(path, optimize=True)
    return path


def main():
    bot.story = improved_story
    bot.backdrop = improved_backdrop
    bot.main()
    metadata_path = bot.OUT / 'metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    report = json.loads((bot.OUT / 'quality_report.json').read_text(encoding='utf-8'))
    write_quality_report(bot.OUT, report, metadata['duration_seconds'])
    print('Cloud v2: sabit kanal açılışı eklendi; kalite raporu hazır; YouTube yüklenmedi.', flush=True)


if __name__ == '__main__':
    main()

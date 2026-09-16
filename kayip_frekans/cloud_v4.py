"""V4 review-driven hardening for KAYIP FREKANS_.

Keeps V3's measured TTS, licensed-photo renderer and no-upload policy, while
adding stricter Turkish-language gates and a dedicated branded first shot.
"""
import re
from PIL import Image, ImageDraw, ImageFont

import cloud_v3 as v3

ORIGINAL_CHECK = v3.check_passage
ORIGINAL_FRAMED = v3.framed_photo

# The previous rendered preview exposed occasional English leakage and malformed
# Turkish. Make those failure modes explicit before narration/rendering starts.
ENGLISH_LEAK = re.compile(
    r"(?i)\b(brother|sister|mother|father|hello|story|final|door|window|room|voice|"
    r"because|then|something|someone|please|thanks|thank you)\b"
)
META_LEAK = re.compile(r"(?i)\b(final story|chapter\s*\d+|scene\s*\d+|prompt|assistant)\b")


def strict_check_passage(text, minimum, maximum):
    text = ORIGINAL_CHECK(text, minimum, maximum)
    issues = []
    if ENGLISH_LEAK.search(text):
        issues.append('İngilizce kelime sızması')
    if META_LEAK.search(text):
        issues.append('model üst-metin sızması')
    # Common malformed output patterns seen in the reviewed preview.
    if re.search(r'(?i)\b(vücutmaçım|zıplama tıbbet|canımın hayalidir)\b', text):
        issues.append('anlamsız veya bozuk Türkçe ifade')
    # Dialogue must remain Turkish too.
    quoted = re.findall(r'[“\"]([^”\"]{2,120})[”\"]', text)
    if any(ENGLISH_LEAK.search(q) for q in quoted):
        issues.append('diyalogda İngilizce ifade')
    if issues:
        raise ValueError('; '.join(issues))
    return text


def branded_framed_photo(path, index):
    result = ORIGINAL_FRAMED(path, index)
    if index != 0:
        return result
    image = Image.open(result).convert('RGB')
    draw = ImageDraw.Draw(image, 'RGBA')
    # First shot belongs to the mandatory channel introduction. Keep the photo
    # visible but make the branding unmistakable and short-lived.
    draw.rounded_rectangle((115, 250, 1805, 790), radius=28,
                           fill=(4, 7, 12, 188), outline=(145, 82, 95, 220), width=4)
    draw.line((180, 365, 1740, 365), fill=(145, 82, 95, 220), width=3)
    title_font = ImageFont.truetype(v3.bot.FONT, 108)
    sub_font = ImageFont.truetype(v3.bot.FONT, 38)
    draw.text((190, 420), 'KAYIP FREKANS_', font=title_font,
              fill=(244, 239, 230, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    draw.text((196, 585), 'Hikâyeye geçmeden önce kulaklığını tak.', font=sub_font,
              fill=(188, 169, 171, 255))
    image.save(result, quality=95)
    return result


# Strengthen the model instruction without replacing V3's proven pipeline.
v3.SYSTEM += (
    ' İngilizce kelime, yapay veya anlaşılmaz Türkçe, çeviri kokan kalıp kullanma. '
    'Diyaloglar da tamamen doğal Türkçe olsun. Somut fiiller ve günlük Türkçe kullan; '
    'anlamı belirsiz süslü ifadeler üretme.'
)
v3.check_passage = strict_check_passage
v3.framed_photo = branded_framed_photo


if __name__ == '__main__':
    v3.main()

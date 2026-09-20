"""Publish a corrected zipper Short with a legible on-screen call to action.

The old renderer showed LIKE + SUBSCRIBE at the very bottom for two seconds,
where YouTube's interface can cover it. Keep the original video and audio
checks; show a large graphic higher up in the frame instead.
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw

import zipper_short as original

SOURCE_FRAME = original.frame


def cta_active(t: float, duration: float) -> bool:
    return duration * 0.52 <= t < duration * 0.67 or duration - 3.2 <= t < duration


def frame(t: float, duration: float, boundaries: list[float]) -> Image.Image:
    image = SOURCE_FRAME(t, duration, boundaries)
    # Remove the older tiny CTA from the bottom edge.
    if duration * 0.56 <= t <= duration * 0.56 + 2.0:
        image.paste(original.BASE.crop((106, 894, 435, 928)), (106, 894))
    if not cta_active(t, duration):
        return image

    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    pulse = (math.sin(t * 4.0) + 1.0) / 2.0
    border = (76, 230, 208, int(210 + 45 * pulse))
    d.rounded_rectangle((33, 246, 507, 348), radius=23,
                        fill=(8, 24, 41, 247), outline=border, width=4)
    d.rounded_rectangle((48, 259, 104, 333), radius=15,
                        fill=(44, 119, 113, 255))
    # Draw a thumb directly; no emoji, stock asset or third-party icon needed.
    d.rounded_rectangle((57, 293, 68, 316), radius=3,
                        fill=(242, 247, 252, 255))
    d.polygon([(70, 294), (77, 282), (81, 271), (86, 271), (90, 278),
               (87, 291), (96, 292), (96, 310), (87, 320), (70, 315)],
              fill=(242, 247, 252, 255))
    d.text((120, 263), 'LIKE + SUBSCRIBE', font=original.font(26, True),
           fill=(242, 247, 252, 255))
    d.text((122, 306), 'MORE HOW-IT-WORKS VIDEOS',
           font=original.font(15, True), fill=(76, 230, 208, 255))
    return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')


def main() -> None:
    if os.getenv('GITHUB_REPOSITORY') != 'averelliq/averelliq.github.io':
        raise RuntimeError('Unexpected repository; upload refused')
    if os.getenv('GITHUB_EVENT_NAME') != 'push' or os.getenv('ZIPPER_CTA_PUBLISH') != '1':
        raise RuntimeError('Only the dedicated CTA correction can publish')
    original.frame = frame
    original.TITLE = 'How a Zipper Works | Animated Explanation'
    original.DESCRIPTION = (
        'An original animation shows how a zipper slider joins two rows of '
        'interlocking teeth and opens them again. More everyday engineering explained.'
    )
    original.main()


if __name__ == '__main__':
    main()

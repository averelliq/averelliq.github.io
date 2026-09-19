"""Require original Full HD portrait stock video before editing or rendering.

Upscaling a 720p source to 1080p cannot restore missing visual detail.
Reject lower-resolution sources rather than silently lowering the standard.
"""
from __future__ import annotations

from typing import Any

import selection_guard

MIN_WIDTH = 1080
MIN_HEIGHT = 1920


def hd_file_options(video: dict[str, Any]) -> list[str]:
    """Choose actual portrait Full HD or better files, never 720p upscales."""
    choices: list[tuple[int, int, str]] = []
    for item in video.get("video_files") or []:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        url = item.get("link")
        if (isinstance(url, str) and url.startswith("https://")
                and height > width and width >= MIN_WIDTH and height >= MIN_HEIGHT):
            # Full-HD source first; higher-resolution files remain valid fallbacks.
            distance = abs(width - MIN_WIDTH) + abs(height - MIN_HEIGHT)
            choices.append((distance, -(width * height), url))
    return [url for _, __, url in sorted(choices)[:2]]


def install() -> None:
    selection_guard._file_options = hd_file_options

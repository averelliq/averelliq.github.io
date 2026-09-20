"""Require genuine native-HD stock video, including usable 4K landscape crops.

A 4K landscape source has enough native pixels for a 1080x1920 portrait
center crop. A regular 1080p landscape source does not; never upscale it.
"""
from __future__ import annotations

from typing import Any

import selection_guard

MIN_WIDTH = 1080
MIN_HEIGHT = 1920


def hd_file_options(video: dict[str, Any]) -> list[str]:
    """Select native >=1080x1920 portrait crops without resolution upscaling."""
    choices: list[tuple[int, int, str]] = []
    for item in video.get("video_files") or []:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        url = item.get("link")
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        # Portrait sources need at least 1080x1920. Landscape sources need
        # at least 1920 vertical pixels for a native 1080x1920 center crop.
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            continue
        crop_width = min(width, int(height * 9 / 16))
        crop_height = min(height, int(width * 16 / 9))
        if crop_width < MIN_WIDTH or crop_height < MIN_HEIGHT:
            continue
        distance = abs(crop_width - MIN_WIDTH) + abs(crop_height - MIN_HEIGHT)
        choices.append((distance, -(width * height), url))
    return [url for _, __, url in sorted(choices)[:2]]


def install() -> None:
    selection_guard._file_options = hd_file_options

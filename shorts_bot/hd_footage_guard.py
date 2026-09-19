"""Reject low-resolution stock sources before selecting or upscaling footage.

Rendered 1080p output alone does not make a 360p source high quality.
"""
from __future__ import annotations

from typing import Any

import selection_guard


def hd_file_options(video: dict[str, Any]) -> list[str]:
    choices: list[tuple[int, str]] = []
    for item in video.get("video_files") or []:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        url = item.get("link")
        if (isinstance(url, str) and url.startswith("https://")
                and height > width and width >= 720 and height >= 1280):
            choices.append((abs(width - 1080) + abs(height - 1920), url))
    return [url for _, url in sorted(choices)[:2]]


def install() -> None:
    selection_guard._file_options = hd_file_options

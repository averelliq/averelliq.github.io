"""Select footage by actual narrated-scene relevance BEFORE expensive rendering.

Reject mismatched clips, detect near-duplicate frames across scenes, try different
Pexels results; if nothing fits, cancel rather than publish random footage.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import requests

import upgrade
import visual_guard

_USED_IDS: set[int] = set()
_USED_FINGERPRINTS: dict[int, int] = {}


def _fingerprint(video: Path) -> int:
    """64-bit difference hash on a middle frame; catches near-identical stock copies."""
    duration = visual_guard._duration(video)
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{duration * 0.5:.3f}", "-i", str(video),
         "-frames:v", "1", "-vf", "scale=9:8,format=gray", "-f", "rawvideo",
         "-pix_fmt", "gray", "-"],
        check=True, capture_output=True,
    )
    pixels = result.stdout
    if len(pixels) != 72:
        raise ValueError("Stock video fingerprint image invalid")
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return bits


def _file_options(video: dict[str, Any]) -> list[str]:
    options: list[tuple[int, str]] = []
    for item in video.get("video_files") or []:
        width, height = int(item.get("width") or 0), int(item.get("height") or 0)
        link = item.get("link")
        if link and height > width and height >= 720 and width >= 360 and link.startswith("https://"):
            options.append((abs(width - 1080) + abs(height - 1920), link))
    return [link for _, link in sorted(options)[:2]]


def _download(link: str, target: Path) -> None:
    with requests.get(link, stream=True, timeout=90) as response:
        response.raise_for_status()
        total = 0
        with target.open("wb") as handle:
            for block in response.iter_content(chunk_size=1024 * 1024):
                if block:
                    total += len(block)
                    if total > 35 * 1024 * 1024:
                        raise ValueError("Candidate exceeds 35 MB")
                    handle.write(block)
    visual_guard._duration(target)


def choose(scene: dict[str, Any], index: int) -> Path:
    if not upgrade.bot.PEXELS_API_KEY:
        upgrade.bot.die("Missing PEXELS_API_KEY; upload cancelled")
    target = upgrade.bot.WORK / f"source_{index:02d}.mp4"
    target.unlink(missing_ok=True)
    max_candidates = max(1, min(9, int(os.getenv("SHORTS_MAX_VISUAL_CANDIDATES", "6"))))
    tried = 0
    reasons: list[str] = []
    seen_on_scene: set[int] = set()
    queries = list(dict.fromkeys([scene["query"], *scene["backup_queries"]]))
    for query in queries:
        try:
            response = requests.get(
                "https://api.pexels.com/v1/videos/search",
                headers={"Authorization": upgrade.bot.PEXELS_API_KEY},
                params={"query": query, "orientation": "portrait", "per_page": 15,
                        "page": 1, "locale": "en-US"}, timeout=45,
            )
            response.raise_for_status()
            videos = response.json().get("videos") or []
        except (requests.RequestException, ValueError, TypeError) as exc:
            reasons.append(f"Search for {query!r}: {type(exc).__name__}")
            continue
        local_count = 0
        for video in videos:
            if tried >= max_candidates or local_count >= 3:
                break
            video_id = video.get("id")
            if type(video_id) is not int or video_id <= 0:
                continue
            if video_id in _USED_IDS or video_id in seen_on_scene:
                continue
            options = _file_options(video)
            if not options:
                continue
            seen_on_scene.add(video_id)
            tried += 1
            local_count += 1
            downloaded = False
            for link in options:
                try:
                    _download(link, target)
                    downloaded = True
                    break
                except (requests.RequestException, subprocess.CalledProcessError,
                        ValueError, OSError) as exc:
                    target.unlink(missing_ok=True)
                    reasons.append(f"Stock {video_id}: {type(exc).__name__}")
            if not downloaded:
                continue
            try:
                fingerprint = _fingerprint(target)
                matching_id = next((other_id for other_id, previous in _USED_FINGERPRINTS.items()
                                    if (fingerprint ^ previous).bit_count() <= 4), None)
                if matching_id is not None:
                    reasons.append(f"Stock {video_id}: visually duplicates scene asset {matching_id}")
                    target.unlink(missing_ok=True)
                    continue
                approved, explanation = visual_guard.review_candidate(
                    scene, target, upgrade.bot.WORK, index)
            except (requests.RequestException, subprocess.CalledProcessError,
                    ValueError, OSError, KeyError, IndexError, TypeError) as exc:
                # API/model outages are not a visual rejection: NEVER upload.
                target.unlink(missing_ok=True)
                upgrade.bot.die(f"Scene {index + 1} preview check unavailable: {type(exc).__name__}: {exc}")
            if not approved:
                reasons.append(f"Stock {video_id} rejected: {explanation}")
                target.unlink(missing_ok=True)
                continue
            _USED_IDS.add(video_id)
            _USED_FINGERPRINTS[video_id] = fingerprint
            scene["selected_stock_query"] = query
            scene["pexels_video_id"] = video_id
            scene["preview_review"] = {"approved": True, "three_frames_checked": True,
                                       "visible_evidence": explanation}
            print(f"Scene {index + 1}: verified stock asset {video_id} ({query!r})", flush=True)
            return target
        if tried >= max_candidates:
            break
    target.unlink(missing_ok=True)
    upgrade.bot.die(
        f"No matching footage for scene {index + 1} after {tried} candidates; "
        f"upload cancelled. Details: {'; '.join(reasons[-8:])[:1100]}"
    )
    raise AssertionError("unreachable")

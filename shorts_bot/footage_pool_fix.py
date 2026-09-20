"""Recover sparse stock searches without weakening visual or audio gates.

Collect subject-specific native-HD footage and require eight distinct filmed
shots to pass conservative visual review before writing or uploading a Short.
"""
from __future__ import annotations

import os
from typing import Any

import requests

import footage_first as first
import hd_footage_guard

MAX_POOL = 54
MAX_CHECKED = 32
REVIEW_BATCH_SIZE = 4
EXTRA_QUERIES = {
    "how an espresso machine brews coffee": (
        "espresso machine brewing", "espresso extraction", "espresso coffee pouring",
        "barista making espresso", "coffee portafilter", "espresso machine coffee",
        "espresso shot closeup", "coffee machine brewing", "barista grinding coffee",
        "espresso crema", "coffee tamping portafilter", "barista coffee preparation",
        "coffee beans grinding", "espresso cup filling", "coffee brewing closeup",
    ),
    "why airplane windows are rounded": (
        "airplane oval window", "airplane cabin windows", "airplane window closeup",
        "passenger airplane window", "airplane interior windows", "airplane wing window",
    ),
    "how a steel gear is made": (
        "steel gear machining", "gear cutting machine", "gear hobbing machine",
        "metal gear manufacturing", "metal gear cnc cutting", "gear teeth milling",
        "industrial gear production", "metal gear inspection", "machined metal gears",
        "gear factory machinery", "industrial machine gears", "gear machining closeup",
    ),
}
_installed = False


def wider_search(topic: str, queries: tuple[str, ...]) -> list[dict[str, Any]]:
    if not first.upgrade.bot.PEXELS_API_KEY:
        raise RuntimeError("Pexels API key missing; no source provenance")
    combined = tuple(dict.fromkeys((*EXTRA_QUERIES.get(topic, ()), *queries)))
    pool: list[dict[str, Any]] = []
    seen: set[int] = set()
    for query in combined:
        if len(pool) >= MAX_POOL:
            break
        for orientation in ("portrait", "landscape"):
            if len(pool) >= MAX_POOL:
                break
            for page in (1, 2):
                response = requests.get(
                    "https://api.pexels.com/v1/videos/search",
                    headers={"Authorization": first.upgrade.bot.PEXELS_API_KEY},
                    params={"query": query, "orientation": orientation,
                            "per_page": 30, "page": page, "locale": "en-US"},
                    timeout=40,
                )
                response.raise_for_status()
                added = 0
                for video in response.json().get("videos", []):
                    identifier = video.get("id")
                    if type(identifier) is not int or identifier <= 0 or identifier in seen:
                        continue
                    options = hd_footage_guard.hd_file_options(video)
                    url = video.get("url")
                    if not options or not isinstance(url, str) or not url.startswith("https://www.pexels.com/video/"):
                        continue
                    seen.add(identifier)
                    pool.append({"id": identifier, "url": url, "query": query,
                                 "file_urls": options})
                    added += 1
                    if added >= 6 or len(pool) >= MAX_POOL:
                        break
                if added >= 6 or len(pool) >= MAX_POOL:
                    break
    print(f"FOOTAGE RECOVERY: {topic!r}, {len(pool)} DISTINCT native-HD stock candidates", flush=True)
    return pool


def review_replacements(topic: str, queries: tuple[str, ...]):
    pool = first._search(topic, queries)
    if len(pool) < first.MIN_SHOTS:
        print("FOOTAGE RECOVERY: not enough distinct native-HD clips exist", flush=True)
        return None
    approved: list[dict[str, Any]] = []
    fingerprints: list[int] = []
    pending: list[dict[str, Any]] = []
    checked = 0

    def review_pending() -> None:
        nonlocal pending
        if not pending:
            return
        # Reviewing four clips in one request instead of pairs lowers API
        # traffic while retaining all three actual frames and every check.
        verdicts = first._vision(topic, pending)
        if len(verdicts) != len(pending):
            raise ValueError("Incomplete footage verdicts; upload blocked")
        for item, verdict in zip(pending, verdicts):
            if verdict:
                approved.append(item)
                print(f"FOOTAGE RECOVERY: approved {len(approved)}/{first.MIN_SHOTS}, stock {item['id']}", flush=True)
            else:
                item["path"].unlink(missing_ok=True)
        pending = []

    for position, candidate in enumerate(pool):
        if checked >= MAX_CHECKED or len(approved) >= first.MIN_SHOTS:
            break
        clip = first._download(candidate, position)
        if clip is None:
            continue
        if any((clip["fingerprint"] ^ previous).bit_count() <= 4 for previous in fingerprints):
            clip["path"].unlink(missing_ok=True)
            continue
        fingerprints.append(clip["fingerprint"])
        pending.append(clip)
        checked += 1
        if len(pending) >= REVIEW_BATCH_SIZE:
            review_pending()
    if pending and len(approved) < first.MIN_SHOTS:
        review_pending()
    if len(approved) < first.MIN_SHOTS:
        print(f"FOOTAGE RECOVERY: only {len(approved)} independently approved after {checked} reviewed; no unsafe fallback", flush=True)
        return None
    for extra in approved[first.MIN_SHOTS:]:
        extra["path"].unlink(missing_ok=True)
    return approved[:first.MIN_SHOTS]


def install() -> None:
    global _installed
    if _installed:
        return
    first._search = wider_search
    first._prepare = review_replacements
    original_candidates = first._candidates

    def candidates(theme: str, seed: str):
        if os.getenv("SHORTS_PREVIEW_LOCK_TOPIC") == "1":
            if seed not in EXTRA_QUERIES:
                raise ValueError("Preview topic not configured; do not substitute topics")
            return [(seed, EXTRA_QUERIES[seed])]
        return original_candidates(theme, seed)

    first._candidates = candidates
    _installed = True

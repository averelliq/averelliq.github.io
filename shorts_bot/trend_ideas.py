"""Find a *topic*, never download or copy another creator's video, audio or script.

Public YouTube metadata is inspiration only. If search permissions, quotas, topic
classification or editorial checks fail, use the existing evergreen topic.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import requests

SEARCH = "https://www.googleapis.com/youtube/v3/search"
VIDEOS = "https://www.googleapis.com/youtube/v3/videos"
QUERIES = {
    "science": "animal science amazing facts shorts",
    "history": "ancient history inventions explained shorts",
    "everyday": "everyday science why things happen shorts",
}
_CACHE: dict[str, str] = {}
_REFERENCES: dict[str, dict[str, Any]] = {}
_BLOCKED = re.compile(r"(?i)\b(prank|challenge|giveaway|reaction|celebrity|politic|election|cure|diagnos|invest|crypto|war footage|movie clip|song|official trailer)\b")


def _credentials() -> tuple[dict[str, str], dict[str, str]]:
    key = os.getenv("YT_DATA_API_KEY", "").strip()
    if key:
        return {}, {"key": key}
    client_id = os.getenv("YT_CLIENT_ID", "").strip()
    client_secret = os.getenv("YT_CLIENT_SECRET", "").strip()
    refresh = os.getenv("YT_REFRESH_TOKEN", "").strip()
    if not all((client_id, client_secret, refresh)):
        raise ValueError("YT_DATA_API_KEY or existing YouTube OAuth credentials required")
    token = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": client_id, "client_secret": client_secret,
              "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=20,
    )
    token.raise_for_status()
    access = token.json().get("access_token")
    if not isinstance(access, str) or not access:
        raise ValueError("No YouTube access token received")
    return {"Authorization": f"Bearer {access}"}, {}


def _duration(value: str) -> int:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return 0
    h, m, s = (int(part or 0) for part in match.groups())
    return h * 3600 + m * 60 + s


def _recent_candidates(theme: str) -> list[dict[str, Any]]:
    headers, auth_params = _credentials()
    since = (datetime.now(timezone.utc) - timedelta(days=21)).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = requests.get(SEARCH, headers=headers,
        params={**auth_params, "part": "snippet", "q": QUERIES[theme], "type": "video",
                "videoDuration": "short", "order": "viewCount", "maxResults": 30,
                "publishedAfter": since, "relevanceLanguage": "en", "regionCode": "US",
                "safeSearch": "strict"}, timeout=30)
    result.raise_for_status()
    ids = [item.get("id", {}).get("videoId") for item in result.json().get("items", [])]
    ids = [video_id for video_id in ids if isinstance(video_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id)]
    if not ids:
        return []
    detail = requests.get(VIDEOS, headers=headers,
        params={**auth_params, "part": "snippet,contentDetails,statistics,status",
                "id": ",".join(ids)}, timeout=30)
    detail.raise_for_status()
    now = datetime.now(timezone.utc)
    candidates: list[dict[str, Any]] = []
    for item in detail.json().get("items", []):
        snippet = item.get("snippet") or {}
        stats = item.get("statistics") or {}
        status = item.get("status") or {}
        title = snippet.get("title", "")
        if not isinstance(title, str) or not 10 <= len(title) <= 110 or _BLOCKED.search(title):
            continue
        if status.get("privacyStatus", "public") != "public":
            continue
        duration = _duration((item.get("contentDetails") or {}).get("duration", ""))
        if not 12 <= duration <= 60:
            continue  # Short-form candidate, not a verified Shorts classification.
        try:
            created = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            views = int(stats.get("viewCount", 0))
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        days = max(0.5, (now - created).total_seconds() / 86400)
        if not 0 <= days <= 22 or views < 15000:
            continue
        candidates.append({"id": item["id"], "title": title, "views": views,
                           "views_per_day": round(views / days), "age_days": round(days, 1)})
    return sorted(candidates, key=lambda item: item["views_per_day"], reverse=True)


def _neutral_topic(theme: str, title: str, model_json: Callable[[str], dict[str, Any]]) -> str | None:
    result = model_json(
        "Extract only an independently explainable general educational TOPIC from this "
        "YouTube video title. This is metadata, not evidence that a claim is true. "
        "Do not reproduce its title, hook, narrative, scene order, phrasing, or creator's "
        "specific creative concept. Reject topics outside the requested category, "
        "unverifiable sensational claims, dangerous instructions, celebrities, politics "
        "and medically or financially consequential claims. The result must be a "
        "plain, neutral 3-9 word English noun phrase about the underlying subject. "
        f"Category: {theme}. Title: {title!r}. "
        'Return ONLY JSON: {"suitable":true,"topic":"neutral subject"} '
        'or {"suitable":false,"topic":""}.'
    )
    if result.get("suitable") is not True:
        return None
    topic = result.get("topic")
    if (not isinstance(topic, str) or not 3 <= len(topic.split()) <= 9
            or len(topic) > 75 or re.search(r"[#@\n\r/:]|https?", topic, re.I)
            or _BLOCKED.search(topic)):
        return None
    return topic.strip()


def pick_topic(theme: str, evergreen: Callable[[str], str],
               model_json: Callable[[str], dict[str, Any]]) -> str:
    if theme in _CACHE:
        return _CACHE[theme]
    fallback = evergreen(theme)
    if os.getenv("SHORTS_TREND_MODE", "auto").lower() == "off":
        _CACHE[theme] = fallback
        return fallback
    try:
        candidates = _recent_candidates(theme)
        # Try a few distinct titles rather than trusting the highest-view video.
        for candidate in candidates[:5]:
            neutral = _neutral_topic(theme, candidate["title"], model_json)
            if neutral:
                _CACHE[theme] = neutral
                _REFERENCES[theme] = {"video_id": candidate["id"],
                    "url": "https://www.youtube.com/watch?v=" + candidate["id"],
                    "title": candidate["title"], "observed_views": candidate["views"],
                    "views_per_day": candidate["views_per_day"],
                    "age_days": candidate["age_days"], "inspired_topic": neutral,
                    "usage": "Metadata/topic only; no original footage, audio or script used"}
                print(f"TREND TOPIC: {neutral}; reference ID: {candidate['id']}; "
                      f"observed views: {candidate['views']}", flush=True)
                return neutral
        print("TREND: no suitable short-form topic; evergreen fallback.", flush=True)
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError, SystemExit) as exc:
        print(f"TREND: discovery unavailable ({type(exc).__name__}); evergreen fallback.", flush=True)
    _CACHE[theme] = fallback
    return fallback


def reference_for(theme: str) -> dict[str, Any] | None:
    return _REFERENCES.get(theme)

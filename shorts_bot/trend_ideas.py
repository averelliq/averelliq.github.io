"""Discover original educational topics from public YouTube metadata only.

A YouTube *upload-only* OAuth refresh token cannot be assumed to authorize
public search. Gemini API keys are also not interchangeable with YouTube keys.
When a dedicated YouTube Data API v3 key is absent or rejected, keep the
existing evergreen topic without attempting to bypass Google's API controls.
Never copy source footage, audio, script, editing or thumbnails.
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


class TrendAccessError(ValueError):
    """Sanitized, actionable diagnostic; never include a credential or URL."""


def _credentials() -> tuple[dict[str, str], dict[str, str]]:
    key = os.getenv("YT_DATA_API_KEY", "").strip()
    if not key:
        raise TrendAccessError(
            "YT_DATA_API_KEY missing: YouTube trend search is OFF. Enable "
            "YouTube Data API v3 in Google Cloud, create a dedicated API key, "
            "and save it as the GitHub Actions secret YT_DATA_API_KEY. "
            "The existing upload OAuth token and GEMINI_API_KEY cannot replace it."
        )
    return {}, {"key": key}


def _response_json(response: requests.Response) -> dict[str, Any]:
    """Report the API's actual error category without leaking URL/key/token."""
    if not response.ok:
        reason = "unknown"
        try:
            error = response.json().get("error", {})
            details = error.get("errors", [])
            if isinstance(details, list) and details and isinstance(details[0], dict):
                reason = str(details[0].get("reason") or "unknown")
            if reason == "unknown" and isinstance(error.get("status"), str):
                reason = error["status"]
        except (ValueError, AttributeError, TypeError):
            pass
        reason = re.sub(r"[^A-Za-z0-9_-]", "", reason)[:45] or "unknown"
        if response.status_code in (401, 403):
            guidance = (
                "Check that YT_DATA_API_KEY is a valid key for a Cloud project "
                "with YouTube Data API v3 enabled; inspect API restrictions "
                "and quota. Upload-only OAuth permissions do not authorize "
                "this request."
            )
        elif response.status_code == 429:
            guidance = "Check YouTube API quota and retry later."
        else:
            guidance = "See YouTube Data API errors and Cloud API dashboard."
        raise TrendAccessError(
            f"YouTube trend metadata HTTP {response.status_code} "
            f"(reason={reason}). {guidance}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise TrendAccessError("YouTube returned unexpected metadata; evergreen fallback")
    return payload


def _duration(value: str) -> int:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return 0
    h, m, s = (int(part or 0) for part in match.groups())
    return h * 3600 + m * 60 + s


def _recent_candidates(theme: str) -> list[dict[str, Any]]:
    headers, auth_params = _credentials()
    since = (datetime.now(timezone.utc) - timedelta(days=21)).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = requests.get(
        SEARCH, headers=headers,
        params={**auth_params, "part": "snippet", "q": QUERIES[theme],
                "type": "video", "videoDuration": "short", "order": "viewCount",
                "maxResults": 30, "publishedAfter": since,
                "relevanceLanguage": "en", "regionCode": "US", "safeSearch": "strict"},
        timeout=30,
    )
    ids = [item.get("id", {}).get("videoId") for item in _response_json(result).get("items", [])]
    ids = [video_id for video_id in ids if isinstance(video_id, str)
           and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id)]
    if not ids:
        return []
    detail = requests.get(
        VIDEOS, headers=headers,
        params={**auth_params, "part": "snippet,contentDetails,statistics,status",
                "id": ",".join(ids)}, timeout=30,
    )
    now = datetime.now(timezone.utc)
    candidates: list[dict[str, Any]] = []
    for item in _response_json(detail).get("items", []):
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
            continue  # Short-form candidate; not a verified Shorts classification.
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
        print("TREND DISABLED: SHORTS_TREND_MODE=off; evergreen topic.", flush=True)
        _CACHE[theme] = fallback
        return fallback
    if not os.getenv("YT_DATA_API_KEY", "").strip():
        print("TREND DISABLED: YT_DATA_API_KEY is missing. Configure the "
              "dedicated YouTube Data API v3 key in GitHub Actions secrets; "
              "evergreen topic used. Do not use GEMINI_API_KEY or upload OAuth.", flush=True)
        _CACHE[theme] = fallback
        return fallback
    try:
        candidates = _recent_candidates(theme)
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
        # Never log a requests.HTTPError URL: YouTube API keys live in query params.
        if isinstance(exc, TrendAccessError):
            print(f"TREND DISABLED: {exc} Evergreen topic used.", flush=True)
        else:
            print(f"TREND: discovery unavailable ({type(exc).__name__}); "
                  "evergreen fallback.", flush=True)
    _CACHE[theme] = fallback
    return fallback


def reference_for(theme: str) -> dict[str, Any] | None:
    return _REFERENCES.get(theme)

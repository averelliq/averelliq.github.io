"""Emergency one-shot Shorts path used when the AI generation run fails.

For a manually verified missed upload, EMERGENCY_FORCE_UPLOAD=1 skips the public
channel duplicate lookup. Normal emergency use stays fail-closed.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta, timezone

import requests

import main as bot

CHANNEL_ID = os.getenv("YT_CHANNEL_ID", "").strip()

PLAN = {
    "title": "Why Soap Beats Grease So Easily #Shorts",
    "description": "Soap has a clever molecular trick that helps water carry grease away. Here is the simple science behind every wash.",
    "tags": ["shorts", "science", "curiosity", "soap", "everyday science"],
    "narration": (
        "Soap does something water alone cannot: it grabs grease. "
        "Each soap molecule has two different ends. One end is attracted to water, "
        "while the other prefers oils and fats. When you scrub, the oil-loving ends "
        "bury themselves in grease. The water-loving ends stay facing outward. "
        "Together they form tiny clusters called micelles, trapping the grease inside. "
        "Then running water carries those clusters away. That is why a little soap can "
        "make stubborn oily messes rinse off so easily."
    ),
    "scenes": [
        {"query": "washing hands soap", "caption": "Soap grabs grease"},
        {"query": "liquid soap closeup", "caption": "Two different ends"},
        {"query": "soap bubbles macro", "caption": "Water loving side"},
        {"query": "greasy pan washing", "caption": "Oil loving side"},
        {"query": "washing dishes sink", "caption": "Surrounding the grease"},
        {"query": "soapy water bubbles", "caption": "Tiny micelles form"},
        {"query": "rinsing dishes water", "caption": "Water carries it"},
        {"query": "clean dishes kitchen", "caption": "Grease rinses away"},
    ],
}


def recent_upload_exists() -> bool:
    if os.getenv("EMERGENCY_FORCE_UPLOAD", "0").strip() == "1":
        print("FORCED ONE-SHOT: prior failed runs verified; duplicate lookup skipped.", flush=True)
        return False
    key = os.getenv("YT_DATA_API_KEY", "").strip()
    if not key or not CHANNEL_ID:
        raise RuntimeError("Emergency duplicate check unavailable; publishing blocked")
    threshold_raw = os.getenv("EMERGENCY_NOT_BEFORE", "").strip()
    threshold = (
        datetime.fromisoformat(threshold_raw.replace("Z", "+00:00"))
        if threshold_raw else datetime.now(timezone.utc) - timedelta(minutes=45)
    )
    channel = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "contentDetails", "id": CHANNEL_ID, "key": key}, timeout=30,
    )
    channel.raise_for_status()
    items = channel.json().get("items") or []
    if not items:
        raise RuntimeError("YouTube channel lookup returned no result")
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    playlist = requests.get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        params={"part": "snippet", "playlistId": uploads, "maxResults": 5, "key": key}, timeout=30,
    )
    playlist.raise_for_status()
    for item in playlist.json().get("items") or []:
        published = ((item.get("snippet") or {}).get("publishedAt") or "").strip()
        video_id = (((item.get("snippet") or {}).get("resourceId") or {}).get("videoId") or "").strip()
        if not published:
            continue
        when = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if when >= threshold:
            print(f"RECENT UPLOAD FOUND: {video_id} at {published}; emergency upload skipped.", flush=True)
            return True
    return False


def main() -> None:
    if recent_upload_exists():
        return
    if bot.WORK.exists():
        shutil.rmtree(bot.WORK)
    bot.WORK.mkdir(parents=True, exist_ok=True)
    bot.OUT.mkdir(parents=True, exist_ok=True)
    (bot.OUT / "plan.json").write_text(json.dumps(PLAN, indent=2), encoding="utf-8")
    audio = bot.WORK / "voice.wav"
    bot.tts(PLAN["narration"], audio)
    final = bot.build_video(PLAN, audio)
    video_id = bot.upload_youtube(final, PLAN)
    if not video_id:
        raise RuntimeError("YouTube upload returned no video id")
    print(f"EMERGENCY UPLOAD COMPLETE: {video_id}", flush=True)


if __name__ == "__main__":
    main()

"""Publish only the exact corrected and inspected espresso MP4, never generate or swap footage."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import requests

ROOT = Path(__file__).resolve().parent
REQUEST = ROOT / "espresso_release_request.json"
ARTIFACT = ROOT / "reviewed_espresso_artifact"
HISTORY_PATH = "shorts_bot/published_history.json"
REPO = "averelliq/averelliq.github.io"
CORRECTED_RUN = 35479892366


def check_video(path: Path, expected_hash: str) -> dict:
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
        raise ValueError("Reviewed MP4 SHA-256 mismatch: refusing upload")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    metadata = json.loads(result.stdout)
    streams = metadata["streams"]
    video_tracks = [s for s in streams if s.get("codec_type") == "video"]
    audio_tracks = [s for s in streams if s.get("codec_type") == "audio"]
    seconds = float(metadata["format"]["duration"])
    if (len(video_tracks) != 1 or len(audio_tracks) != 1 or
            video_tracks[0].get("width") != 1080 or video_tracks[0].get("height") != 1920 or
            video_tracks[0].get("codec_name") != "h264" or
            audio_tracks[0].get("codec_name") != "aac" or
            not 20 <= seconds <= 58 or path.stat().st_size < 1_000_000):
        raise ValueError("Reviewed Short does not have required picture/audio format")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
                   check=True, capture_output=True)
    return {"duration": round(seconds, 2), "bytes": path.stat().st_size}


def github_get_history(session):
    url = f"https://api.github.com/repos/{REPO}/contents/{HISTORY_PATH}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    blob = response.json()
    content = json.loads(base64.b64decode(blob["content"]).decode("utf-8"))
    if not isinstance(content, list):
        raise ValueError("Published history is corrupted")
    return url, blob["sha"], content


def github_save_history(session, url, sha, items, message):
    response = session.put(url, json={
        "message": message, "sha": sha,
        "content": base64.b64encode((json.dumps(items, indent=2, ensure_ascii=False) + "\n").encode()).decode(),
    }, timeout=40)
    response.raise_for_status()


def youtube_upload(path: Path) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    credentials = Credentials(
        token=None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    credentials.refresh(Request())
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    title = "How Espresso Really Works"
    description = ("See how an espresso machine brews a concentrated coffee shot, "
                   "from the portafilter to the first drops. Follow for more everyday mysteries.")
    tags = ["espresso", "coffee", "espresso machine", "barista", "coffee brewing"]
    body = {"snippet": {"title": title, "description": description, "tags": tags,
                        "categoryId": "27", "defaultLanguage": "en"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=8 * 1024 * 1024,
                            resumable=True)
    operation = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    result = None
    while result is None:
        progress, result = operation.next_chunk()
        if progress:
            print(f"YOUTUBE UPLOAD PROGRESS: {int(progress.progress() * 100)}%", flush=True)
    video_id = result.get("id") if isinstance(result, dict) else None
    if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise RuntimeError("YouTube response lacks valid video ID; check channel before retrying")
    print(f"YOUTUBE UPLOAD RESPONSE: https://www.youtube.com/watch?v={video_id}", flush=True)
    return video_id


def main():
    if os.environ.get("GITHUB_EVENT_NAME") != "push" or os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise RuntimeError("Only the dedicated repository push may publish")
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    if set(request) != {"approved_after_manual_review", "publish_public", "source_run_id", "mp4_sha256"}:
        raise ValueError("Release request contains unexpected or missing fields")
    if request["approved_after_manual_review"] is not True or request["publish_public"] is not True:
        raise ValueError("Explicit review approval and public-publish flags required")
    if request["source_run_id"] != CORRECTED_RUN:
        raise ValueError("Rejected/incorrect source workflow run")
    expected_hash = request["mp4_sha256"]
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_hash):
        raise ValueError("Exact corrected MP4 fingerprint required")
    video = ARTIFACT / "short.mp4"
    info = check_video(video, expected_hash)
    plan = json.loads((ARTIFACT / "plan.json").read_text(encoding="utf-8"))
    scenes = plan.get("scenes", [])
    ids = [scene.get("pexels_video_id") for scene in scenes]
    if (plan.get("topic") != "how an espresso machine brews coffee"
            or plan.get("preview_only") is not True
            or plan.get("independent_source_review_run") != "35478572542"
            or len(scenes) < 6 or len(set(ids)) != len(ids)
            or not all(type(i) is int and i > 0 for i in ids)
            or "portafilter goes into place" not in scenes[0].get("voiceover", "")
            or "cup waits beneath" not in scenes[3].get("voiceover", "")):
        raise ValueError("Video content, correction or footage provenance differs from inspected edit")
    if not (ARTIFACT / "manual_review_required.txt").is_file():
        raise ValueError("Missing transparent review evidence")
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28"})
    url, sha, history = github_get_history(session)
    if any((item.get("topic") in (plan["topic"], "espresso machine brews coffee")
            and item.get("state") in ("reserved", "publishing", "published"))
           or item.get("mp4_sha256") == expected_hash for item in history):
        raise ValueError("Duplicate/pending espresso Short in history; do NOT re-upload")
    record = {"topic": plan["topic"], "mp4_sha256": expected_hash,
              "title": "How Espresso Really Works", "state": "publishing",
              "at": datetime.now(timezone.utc).isoformat(),
              "source_run_id": str(request["source_run_id"]),
              "publish_run_id": os.environ.get("GITHUB_RUN_ID", "unknown")}
    history.append(record)
    github_save_history(session, url, sha, history, "Reserve corrected reviewed espresso upload to prevent duplicate video")
    print(f"UPLOAD RESERVED: {info}; corrected reviewed MP4 fingerprint matched", flush=True)
    video_id = youtube_upload(video)
    url, sha, refreshed = github_get_history(session)
    matches = [r for r in refreshed if r.get("mp4_sha256") == expected_hash
               and r.get("state") == "publishing"]
    if len(matches) != 1:
        raise ValueError("Upload succeeded but publishing ledger inconsistent; video ID in logs")
    matches[0]["state"] = "published"
    matches[0]["video_id"] = video_id
    matches[0]["at"] = datetime.now(timezone.utc).isoformat()
    github_save_history(session, url, sha, refreshed, "Record published corrected original espresso Short")
    receipt = {"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
               "privacy": "public", "mp4_sha256": expected_hash,
               "duration_seconds": info["duration"]}
    (ARTIFACT / "publication_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"PUBLISHED AND RECORDED: {receipt['url']}", flush=True)


if __name__ == "__main__":
    main()

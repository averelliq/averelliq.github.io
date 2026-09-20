"""Publish ONLY the exact manually reviewed pottery preview, once.

Never regenerate footage or synthesize narration in the release job.
"""
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
ARTIFACT = ROOT / "reviewed_pottery_artifact"
REQUEST = ROOT / "pottery_release_request.json"
HISTORY = "shorts_bot/published_history.json"
REPO = "averelliq/averelliq.github.io"
PREVIEW_RUN = 35480740029
TOPIC = "how a potter shapes a clay bowl on a wheel"


def verify(path: Path, expected_sha256: str) -> float:
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Reviewed pottery MP4 does not match exact approved file")
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout)
    tracks = info["streams"]
    picture = [s for s in tracks if s.get("codec_type") == "video"]
    sound = [s for s in tracks if s.get("codec_type") == "audio"]
    seconds = float(info["format"]["duration"])
    if (len(picture) != 1 or len(sound) != 1 or
            int(picture[0]["width"]) != 1080 or int(picture[0]["height"]) != 1920 or
            picture[0].get("codec_name") != "h264" or sound[0].get("codec_name") != "aac" or
            not 20 <= seconds <= 58 or path.stat().st_size < 1_000_000):
        raise ValueError("Pottery MP4 codec, tracks, duration or quality gate failed")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                   check=True, capture_output=True)
    return seconds


def fetch_history(session):
    url = f"https://api.github.com/repos/{REPO}/contents/{HISTORY}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    history = json.loads(base64.b64decode(payload["content"]).decode("utf-8"))
    if not isinstance(history, list):
        raise ValueError("Publication history is corrupted")
    return url, payload["sha"], history


def save_history(session, url, sha, entries, commit_message):
    response = session.put(url, json={
        "message": commit_message, "sha": sha,
        "content": base64.b64encode((json.dumps(entries, ensure_ascii=False, indent=2) + "\n").encode()).decode(),
    }, timeout=40)
    response.raise_for_status()


def upload(video: Path) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    credentials = Credentials(
        token=None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    credentials.refresh(Request())
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    body = {"snippet": {
        "title": "How Clay Becomes a Bowl",
        "description": "Watch a potter shape clay on a spinning wheel, from the first touch to the forming bowl.",
        "tags": ["pottery", "pottery wheel", "clay", "ceramics", "craftsmanship"],
        "categoryId": "27", "defaultLanguage": "en",
    }, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    request = youtube.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024,
                                   resumable=True),
    )
    response = None
    while response is None:
        progress, response = request.next_chunk()
        if progress:
            print(f"POTTERY UPLOAD: {int(progress.progress() * 100)}%", flush=True)
    video_id = response.get("id") if isinstance(response, dict) else None
    if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise RuntimeError("YouTube response missing usable ID; check channel before any retry")
    print(f"POTTERY YOUTUBE RESPONSE: https://www.youtube.com/watch?v={video_id}", flush=True)
    return video_id


def main():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    if not (request.get("approved_after_audiovisual_review") is True and
            request.get("publish_public") is True and
            request.get("source_run_id") == PREVIEW_RUN):
        raise ValueError("Exact preview and explicit audiovisual review approval required")
    digest = request.get("mp4_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Exact reviewed video fingerprint required")
    video = ARTIFACT / "short.mp4"
    seconds = verify(video, digest)
    plan = json.loads((ARTIFACT / "plan.json").read_text(encoding="utf-8"))
    sources = json.loads((ARTIFACT / "visual_sources.json").read_text(encoding="utf-8"))
    ids = [s.get("pexels_video_id") for s in plan.get("scenes", [])]
    if (plan.get("topic") != TOPIC or not plan.get("preview_only") or
            len(ids) != 7 or len(sources) != 7 or len(set(ids)) != 7 or
            any(type(item) is not int or item <= 0 for item in ids) or
            not (ARTIFACT / "manual_review_required.txt").is_file()):
        raise ValueError("Reviewed edit, source provenance or review evidence missing")
    if not all((ARTIFACT / f"scene_{i:02d}_{moment}.jpg").is_file()
               for i in range(1, 8) for moment in range(1, 4)):
        raise ValueError("Missing required 21 preview frames")
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28"})
    url, sha, history = fetch_history(session)
    if any((row.get("topic") == TOPIC and row.get("state") in ("reserved", "publishing", "published"))
           or row.get("mp4_sha256") == digest for row in history):
        raise ValueError("Identical video already reserved or published; refusing duplicate")
    history.append({"topic": TOPIC, "mp4_sha256": digest,
                    "title": "How Clay Becomes a Bowl", "state": "publishing",
                    "at": datetime.now(timezone.utc).isoformat(),
                    "source_run_id": str(PREVIEW_RUN),
                    "publish_run_id": os.environ.get("GITHUB_RUN_ID", "unknown")})
    save_history(session, url, sha, history, "Reserve reviewed original pottery Short once")
    print(f"POTTERY UPLOAD RESERVED: verified {seconds:.2f}s reviewed MP4", flush=True)
    video_id = upload(video)
    url, sha, refreshed = fetch_history(session)
    matches = [row for row in refreshed if row.get("mp4_sha256") == digest
               and row.get("state") == "publishing"]
    if len(matches) != 1:
        raise RuntimeError("Upload response received but history reconciliation failed; do not retry")
    matches[0]["state"] = "published"
    matches[0]["video_id"] = video_id
    matches[0]["at"] = datetime.now(timezone.utc).isoformat()
    save_history(session, url, sha, refreshed, "Record successfully published pottery Short")
    receipt = {"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
               "privacy": "public", "mp4_sha256": digest, "duration_seconds": round(seconds, 2)}
    (ARTIFACT / "publication_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"POTTERY PUBLISHED: {receipt['url']}", flush=True)


if __name__ == "__main__":
    main()

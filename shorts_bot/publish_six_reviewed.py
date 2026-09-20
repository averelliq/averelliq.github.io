"""Publish only fingerprint-pinned, manually reviewed Shorts previews.

Never renders or swaps any video in the publishing job. Reservations in GitHub
history prevent accidental double uploads. Quota errors defer, not duplicate.
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
APPROVAL = ROOT / "six_shorts_release.json"
ARTIFACTS = ROOT / "six_reviewed"
REPO = "averelliq/averelliq.github.io"
HISTORY = "shorts_bot/published_history.json"
RUN_ID = 35482216058
NAMES = {"3d-printer", "bread", "blacksmith", "sewing", "sushi", "flowers"}


def github():
    session = requests.Session()
    session.headers.update({"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28"})
    return session


def history(session):
    url = f"https://api.github.com/repos/{REPO}/contents/{HISTORY}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    rows = json.loads(base64.b64decode(data["content"]).decode())
    if not isinstance(rows, list):
        raise ValueError("Invalid publication history")
    return url, data["sha"], rows


def commit_history(session, url, sha, rows, message):
    content = base64.b64encode((json.dumps(rows, indent=2, ensure_ascii=False) + "\n").encode()).decode()
    response = session.put(url, json={"message": message, "sha": sha, "content": content}, timeout=35)
    response.raise_for_status()


def verified_video(item):
    name = item.get("name")
    digest = item.get("mp4_sha256")
    if (name not in NAMES or item.get("approved_after_visual_review") is not True
            or type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
        raise ValueError("Unknown, unapproved or unpinned video")
    folder = ARTIFACTS / f"curiorush-six-{name}-{RUN_ID}"
    video = folder / "short.mp4"
    if not video.is_file() or hashlib.sha256(video.read_bytes()).hexdigest() != digest:
        raise ValueError(f"Exact reviewed MP4 fingerprint mismatch: {name}")
    plan = json.loads((folder / "plan.json").read_text())
    sources = json.loads((folder / "visual_sources.json").read_text())
    if (plan.get("preview_only") is not True or plan.get("batch_topic") != name
            or plan.get("topic") != item.get("topic") or plan.get("title") != item.get("title")
            or plan.get("description") != item.get("description")
            or len(plan.get("scenes", [])) != 7 or len(sources) != 7
            or not (folder / "manual_review_required.txt").is_file()
            or any(not (folder / f"scene_{i:02d}_{moment}.jpg").is_file()
                   for i in range(1, 8) for moment in range(1, 4))):
        raise ValueError(f"Missing reviewed visual/metadata evidence: {name}")
    ids = [entry.get("pexels_video_id") for entry in sources]
    if len(set(ids)) != 7 or any(type(i) is not int or i <= 0 for i in ids):
        raise ValueError(f"Duplicated or missing original source IDs: {name}")
    title, description = plan["title"], plan["description"]
    if not (isinstance(title, str) and 8 <= len(title) <= 55
            and isinstance(description, str) and 8 <= len(description) <= 125
            and "#" not in description):
        raise ValueError(f"Title/description failed concise metadata rules: {name}")
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                      "-of", "json", str(video)], check=True,
                                     capture_output=True, text=True).stdout)
    streams = info["streams"]
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    seconds = float(info["format"]["duration"])
    if (len(videos) != 1 or len(audios) != 1 or videos[0].get("codec_name") != "h264"
            or audios[0].get("codec_name") != "aac" or videos[0].get("width") != 1080
            or videos[0].get("height") != 1920 or not 20 <= seconds <= 58
            or video.stat().st_size < 1000000):
        raise ValueError(f"Invalid final MP4 size, codec, duration or 9:16 format: {name}")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"],
                   check=True, capture_output=True)
    return video, plan, seconds


def publish(video, plan):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(token=None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"],
                        client_secret=os.environ["YT_CLIENT_SECRET"],
                        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    creds.refresh(Request())
    client = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {"snippet": {"title": plan["title"], "description": plan["description"],
                        "tags": plan.get("tags", [])[:8], "categoryId": "27",
                        "defaultLanguage": "en"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    request = client.videos().insert(part="snippet,status", body=body,
                                     media_body=MediaFileUpload(str(video), mimetype="video/mp4",
                                                                chunksize=8 * 1024 * 1024,
                                                                resumable=True))
    response = None
    while response is None:
        progress, response = request.next_chunk()
        if progress:
            print(f"UPLOAD {plan['batch_topic']}: {progress.progress():.0%}", flush=True)
    video_id = response.get("id") if isinstance(response, dict) else None
    if not isinstance(video_id, str) or re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id) is None:
        raise RuntimeError("Missing YouTube video ID; DO NOT retry an uncertain upload")
    return video_id


def main():
    manifest = json.loads(APPROVAL.read_text(encoding="utf-8"))
    items = manifest.get("approved_videos")
    if (manifest.get("source_run_id") != RUN_ID or not isinstance(items, list)
            or not 1 <= len(items) <= 6 or len({item.get("name") for item in items}) != len(items)):
        raise ValueError("Missing independent batch review authorization")
    session = github()
    receipts = []
    for item in items:
        video, plan, seconds = verified_video(item)
        name, digest = item["name"], item["mp4_sha256"]
        url, sha, rows = history(session)
        duplicates = [row for row in rows if row.get("mp4_sha256") == digest or
                      (row.get("topic") == plan["topic"] and row.get("state") in
                       ("reserved", "publishing", "published", "deferred_quota"))]
        if len(duplicates) > 1:
            raise RuntimeError("Conflicting historic upload reservations; stop")
        if duplicates and duplicates[0].get("state") == "published":
            print(f"ALREADY PUBLISHED {name}: {duplicates[0].get('video_id')}", flush=True)
            receipts.append({"name": name, "video_id": duplicates[0]["video_id"],
                             "state": "published"})
            continue
        if duplicates and duplicates[0].get("state") != "deferred_quota":
            raise RuntimeError(f"Ambiguous reserved upload for {name}; do not retry")
        if duplicates:
            reservation = duplicates[0]
            reservation["state"] = "publishing"
            reservation["publish_run_id"] = os.environ.get("GITHUB_RUN_ID", "unknown")
        else:
            reservation = {"topic": plan["topic"], "mp4_sha256": digest,
                           "title": plan["title"], "state": "publishing",
                           "source_run_id": str(RUN_ID),
                           "publish_run_id": os.environ.get("GITHUB_RUN_ID", "unknown")}
            rows.append(reservation)
        reservation["at"] = datetime.now(timezone.utc).isoformat()
        commit_history(session, url, sha, rows, f"Reserve one reviewed Short: {name}")
        print(f"VERIFIED AND RESERVED {name}: {seconds:.2f}s", flush=True)
        try:
            youtube_id = publish(video, plan)
        except Exception as exc:
            from googleapiclient.errors import HttpError
            if isinstance(exc, HttpError) and exc.resp.status == 403 and b"quota" in exc.content.lower():
                url, sha, rows = history(session)
                matches = [r for r in rows if r.get("mp4_sha256") == digest and r.get("state") == "publishing"]
                if len(matches) == 1:
                    matches[0]["state"] = "deferred_quota"
                    matches[0]["at"] = datetime.now(timezone.utc).isoformat()
                    commit_history(session, url, sha, rows, f"Defer quota-limited Short: {name}")
                print(f"YOUTUBE QUOTA DEFERRED {name}: leave unpublished until quota renews", flush=True)
                receipts.append({"name": name, "state": "deferred_quota"})
                break
            raise
        url, sha, rows = history(session)
        matches = [r for r in rows if r.get("mp4_sha256") == digest and r.get("state") == "publishing"]
        if len(matches) != 1:
            raise RuntimeError("YouTube upload succeeded but history is ambiguous; DO NOT re-upload")
        matches[0]["state"] = "published"
        matches[0]["video_id"] = youtube_id
        matches[0]["at"] = datetime.now(timezone.utc).isoformat()
        commit_history(session, url, sha, rows, f"Record successful reviewed Short: {name}")
        print(f"PUBLISHED {name}: https://www.youtube.com/watch?v={youtube_id}", flush=True)
        receipts.append({"name": name, "state": "published", "video_id": youtube_id,
                         "url": f"https://www.youtube.com/watch?v={youtube_id}"})
    (ARTIFACTS / "publication_receipts.json").write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    print("BATCH PUBLICATION REPORT: " + json.dumps(receipts), flush=True)


if __name__ == "__main__":
    main()

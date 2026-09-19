"""Originality, human-readable metadata and cross-run duplicate protection.

Uses licensed camera footage through the existing visual gate. Never bypasses
YouTube's realistic synthetic-media disclosure requirements.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

import editorial_upgrade
import main as bot

HISTORY_PATH = "shorts_bot/published_history.json"
TOOL_NAMES = re.compile(r"\b(?:Gemini|ChatGPT|OpenAI|Kokoro|Pexels|Midjourney|Runway|AI[- ]generated|made with AI)\b", re.I)
HASHTAG = re.compile(r"(?<!\w)#[A-Za-z0-9_]+\b")
STOP = {"why", "how", "what", "the", "this", "that", "with", "from", "into", "does", "your", "about", "shorts", "video", "amazing", "viral", "everyday", "mysteries", "explained"}


def _words(value: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", value.lower()) if word not in STOP]


def _slug(value: str) -> str:
    return " ".join(_words(value))


def metadata(plan: dict) -> None:
    """Keep the headline brief, truthful and free from generic hashtags."""
    title = HASHTAG.sub("", str(plan.get("title", "")))
    title = re.sub(r"\s*[|–—:-]\s*(?:Everyday Mysteries|Curiosity Rush)\s*$", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" -|:;,.!?")
    if not 8 <= len(title) <= 52 or TOOL_NAMES.search(title):
        raise ValueError("Headline must be an accurate, interesting 8-52 character title without hashtags or AI-tool names")
    raw = bot.clean_description(str(plan.get("description", "")))
    raw = HASHTAG.sub("", raw)
    # Promotional production notes are not relevant to a viewer's topic.
    sentences = re.split(r"(?<=[.!?])\s+|\s*[|\n]\s*", raw)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip() and not TOOL_NAMES.search(sentence)
                 and not re.fullmatch(r"Everyday Mysteries[.!]?", sentence.strip(), re.I)]
    description = " ".join(sentences[:2]).strip()
    if len(description) > 220:
        description = description[:220].rsplit(" ", 1)[0].rstrip(" ,;:") + "."
    if not description or re.search(r"https?://|www\.|#\w+", description, re.I):
        raise ValueError("Missing or invalid topic-focused description")
    topic = str(plan.get("topic", "")).strip()
    if not 5 <= len(topic) <= 100:
        raise ValueError("Missing precise subject for original Short")
    candidates = [topic, *(_words(title)[:5]), str(plan.get("theme", ""))]
    tags = []
    for tag in candidates:
        tag = str(tag).strip().lower()
        if tag and tag not in tags and tag not in {"shorts", "ai", "viral", "curiosity"}:
            tags.append(tag[:35])
    if len(tags) < 3:
        raise ValueError("Too few subject-specific keywords")
    plan["title"] = title
    plan["description"] = description
    plan["tags"] = tags[:8]
    plan["metadata_review"] = "short title, relevant keywords, no production advertising or hashtags"


def _credentials() -> tuple[str, str]:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if not token or not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise RuntimeError("GitHub history credentials unavailable; upload safely cancelled")
    return token, repository


def _history() -> tuple[list[dict], str | None, str, dict]:
    token, repository = _credentials()
    url = f"https://api.github.com/repos/{repository}/contents/{HISTORY_PATH}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    response = requests.get(url, headers=headers, timeout=25)
    if response.status_code == 404:
        return [], None, url, headers
    response.raise_for_status()
    payload = response.json()
    entries = json.loads(base64.b64decode(payload["content"]).decode("utf-8"))
    if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
        raise ValueError("Invalid existing publication history; upload cancelled")
    return entries, payload["sha"], url, headers


def _store(entries: list[dict], sha: str | None, url: str, headers: dict, message: str) -> None:
    payload = {"message": message, "content": base64.b64encode(
        (json.dumps(entries[-350:], ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    ).decode("ascii")}
    if sha:
        payload["sha"] = sha
    response = requests.put(url, headers=headers, json=payload, timeout=35)
    response.raise_for_status()  # Fail closed on permission failure or concurrent modification.


def _reserve(plan: dict) -> str:
    entries, sha, url, headers = _history()
    topic = _slug(str(plan["topic"]))
    digest = hashlib.sha256(re.sub(r"\s+", " ", plan["narration"].lower()).strip().encode()).hexdigest()
    now = datetime.now(timezone.utc)
    for existing in entries:
        previous = str(existing.get("topic", ""))
        shared = set(topic.split()) & set(previous.split())
        union = set(topic.split()) | set(previous.split())
        similar = bool(union) and len(shared) >= 2 and len(shared) / len(union) >= .8
        if existing.get("narration_sha256") == digest or (topic and (topic == previous or similar)):
            raise ValueError("Topic or narration already published/reserved; upload cancelled to avoid duplicate Shorts")
    reservation = {"topic": topic, "narration_sha256": digest,
                   "title": plan["title"], "state": "reserved", "at": now.isoformat(),
                   "run_id": os.getenv("GITHUB_RUN_ID", "")}
    entries.append(reservation)
    _store(entries, sha, url, headers, "Reserve unique Shorts topic before YouTube upload")
    return digest


def _complete(digest: str, video_id: str) -> None:
    entries, sha, url, headers = _history()
    matches = [entry for entry in entries if entry.get("narration_sha256") == digest]
    if len(matches) != 1 or matches[0].get("state") != "reserved":
        raise RuntimeError("Upload completed but history reservation cannot be reconciled; manual review needed")
    matches[0]["state"] = "published"
    matches[0]["video_id"] = video_id
    _store(entries, sha, url, headers, "Record successfully published unique Short")


def upload(video_path: Path, plan: dict) -> str:
    """Store a durable reservation first; unknown upload outcome is never retried."""
    metadata(plan)
    if not video_path.is_file():
        raise ValueError("No validated video file to upload")
    digest = _reserve(plan)
    client_id = os.getenv("YT_CLIENT_ID", "").strip()
    client_secret = os.getenv("YT_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("YT_REFRESH_TOKEN", "").strip()
    if not all((client_id, client_secret, refresh_token)):
        raise RuntimeError("Missing YouTube OAuth credentials; publication reserved but not uploaded")
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    credentials = Credentials(token=None, refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token", client_id=client_id,
        client_secret=client_secret, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    credentials.refresh(Request())
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    status = {"privacyStatus": bot.YOUTUBE_PRIVACY, "selfDeclaredMadeForKids": False}
    # Never suppress the platform's disclosure when realistic synthetic media exists.
    if plan.get("contains_synthetic_media") is True:
        status["containsSyntheticMedia"] = True
    body = {"snippet": {"title": plan["title"], "description": plan["description"],
             "tags": plan["tags"], "categoryId": "27", "defaultLanguage": "en"},
            "status": status}
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    result = None
    while result is None:
        progress, result = request.next_chunk()
        if progress:
            print(f"YouTube upload: {int(progress.progress() * 100)}%", flush=True)
    video_id = result.get("id") if isinstance(result, dict) else None
    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise RuntimeError("YouTube returned no valid video ID; reservation retained to prevent duplicate")
    _complete(digest, video_id)
    print(f"Published original Short: https://www.youtube.com/watch?v={video_id}", flush=True)
    return video_id


def install() -> None:
    # Change the original model's brief, not YouTube's disclosure obligations.
    editorial_upgrade.POLICY += ("\nORIGINALITY: Create a fresh, independently written story with a specific "
        "angle and non-interchangeable beats. Avoid repeating generic hooks, "
        "template narration, stock montages or previous videos. Show the exact "
        "subject in genuine high-resolution moving camera footage. Sound like "
        "a natural English presenter, not a robotic advertisement. Title MUST "
        "be a short, accurate curiosity headline of 8-52 characters WITHOUT "
        "hashtags. Description: one or two subject-specific sentences, NO "
        "hashtags, tool names, production credits or promotional series labels. "
        "Tags: relevant subject keywords only. Never misrepresent fabricated "
        "footage as evidence of an actual event.\n")
    bot.upload_youtube = upload

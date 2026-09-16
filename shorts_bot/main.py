from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
import soundfile as sf

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
OUT = ROOT / "output"
WORK.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
TTS_VOICE = os.getenv("TTS_VOICE", "am_michael").strip()
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "public").strip()


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: Path) -> float:
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(p.stdout.strip())


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def generate_plan() -> dict[str, Any]:
    if not GEMINI_API_KEY:
        die("Missing GEMINI_API_KEY GitHub secret.")

    seed = f"{os.getenv('GITHUB_RUN_ID', 'local')}-{random.randint(1000, 999999)}"
    prompt = f"""
You create high-retention English YouTube Shorts for a broad international audience.
Create ONE original evergreen curiosity Short. Seed: {seed}.

Rules:
- 34-48 seconds spoken length, about 95-125 words.
- Hook in the first sentence; no greeting, no channel intro.
- Topic must be safe, brand-safe, evergreen and visually searchable in stock footage.
- Prefer space, animals, nature, engineering, geography, ancient history, everyday science, or surprising objects.
- No politics, elections, medical advice, finance advice, dangerous challenges, graphic violence, sexual content, copyrighted characters, celebrity gossip, or breaking news.
- Do not invent precise statistics, quotes, records, or disputed claims. If a fact is uncertain, do not use it.
- Make each sentence easy for a natural English narrator to read.
- Every 5-8 seconds introduce a new visual or curiosity beat.
- End with a satisfying reveal or thought, not with 'like and subscribe'.
- Pexels search queries must be simple English visual phrases, 2-5 words, with no trademarks.
- Output STRICT JSON only, no markdown.

JSON shape:
{{
  "title": "under 70 characters, compelling but accurate, include #Shorts",
  "description": "2 short English sentences",
  "narration": "complete voiceover",
  "tags": ["shorts", "curiosity", "..."],
  "scenes": [
    {{"query": "stock footage search", "caption": "3-7 word on-screen idea"}}
  ]
}}

Use 6-8 scenes. Make narration and scene sequence tell one coherent story.
""".strip()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 8192,
        },
    }
    r = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if not r.ok:
        die(f"Gemini API failed: {r.status_code} {r.text[:500]}")
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        plan = extract_json(text)
    except Exception as exc:
        finish_reason = ((data.get("candidates") or [{}])[0]).get("finishReason")
        die(f"Could not parse Gemini response: {exc}; finishReason={finish_reason}; response={data}")

    narration = str(plan.get("narration", "")).strip()
    scenes = plan.get("scenes") or []
    if len(narration.split()) < 70 or not isinstance(scenes, list) or len(scenes) < 4:
        die(f"Gemini returned an incomplete plan: {plan}")
    return plan


def pexels_video(query: str, index: int) -> Path:
    if not PEXELS_API_KEY:
        die("Missing PEXELS_API_KEY GitHub secret.")
    endpoint = "https://api.pexels.com/v1/videos/search"
    r = requests.get(
        endpoint,
        headers={"Authorization": PEXELS_API_KEY},
        params={
            "query": query,
            "orientation": "portrait",
            "size": "medium",
            "per_page": 12,
            "page": random.randint(1, 3),
            "locale": "en-US",
        },
        timeout=45,
    )
    if not r.ok:
        die(f"Pexels search failed for {query!r}: {r.status_code} {r.text[:300]}")
    videos = r.json().get("videos") or []
    if not videos:
        if query != "nature texture":
            return pexels_video("nature texture", index)
        die("Pexels returned no usable videos.")

    random.shuffle(videos)
    candidates: list[tuple[int, str]] = []
    for v in videos:
        for f in v.get("video_files") or []:
            w, h = int(f.get("width") or 0), int(f.get("height") or 0)
            link = f.get("link")
            if not link or not w or not h:
                continue
            if h >= w and h >= 720:
                score = abs(h - 1920) + abs(w - 1080)
                candidates.append((score, link))
    if not candidates:
        for v in videos:
            for f in v.get("video_files") or []:
                link = f.get("link")
                if link:
                    candidates.append((999999, link))
    if not candidates:
        die(f"No downloadable Pexels file for {query!r}")

    candidates.sort(key=lambda x: x[0])
    link = random.choice(candidates[: min(5, len(candidates))])[1]
    dest = WORK / f"source_{index:02d}.mp4"
    with requests.get(link, stream=True, timeout=120) as dl:
        dl.raise_for_status()
        with dest.open("wb") as f:
            for chunk in dl.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return dest


def tts(text: str, dest: Path) -> None:
    try:
        from kokoro import KPipeline
    except Exception as exc:
        die(f"Kokoro import failed: {exc}")

    pipeline = KPipeline(lang_code="a")
    chunks = []
    for _gs, _ps, audio in pipeline(text, voice=TTS_VOICE, speed=1.03):
        chunks.append(audio)
    if not chunks:
        die("Kokoro produced no audio.")

    import numpy as np

    waveform = np.concatenate(chunks)
    sf.write(dest, waveform, 24000)


def split_captions(text: str, duration: float) -> list[tuple[float, float, str]]:
    words = text.split()
    groups: list[list[str]] = []
    i = 0
    while i < len(words):
        n = 6 if len(words) - i > 7 else len(words) - i
        groups.append(words[i : i + n])
        i += n

    weights = [max(1, sum(len(w) for w in g)) for g in groups]
    total = sum(weights)
    t = 0.0
    items = []
    for idx, (group, weight) in enumerate(zip(groups, weights)):
        span = duration * weight / total
        start = t
        end = duration if idx == len(groups) - 1 else min(duration, t + span)
        items.append((start, end, " ".join(group)))
        t = end
    return items


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(text: str, duration: float, path: Path) -> None:
    rows = []
    for i, (start, end, caption) in enumerate(split_captions(text, duration), 1):
        rows.append(f"{i}\n{srt_time(start)} --> {srt_time(end)}\n{caption}\n")
    path.write_text("\n".join(rows), encoding="utf-8")


def build_video(plan: dict[str, Any], audio_path: Path) -> Path:
    scenes = plan["scenes"]
    duration = ffprobe_duration(audio_path)
    scene_duration = duration / len(scenes)
    clips: list[Path] = []

    for i, scene in enumerate(scenes):
        query = str(scene.get("query") or "nature texture")
        src = pexels_video(query, i)
        clip = WORK / f"clip_{i:02d}.mp4"
        run(
            [
                "ffmpeg",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(src),
                "-t",
                f"{scene_duration:.3f}",
                "-an",
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "21",
                "-pix_fmt",
                "yuv420p",
                str(clip),
            ]
        )
        clips.append(clip)

    concat_file = WORK / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8"
    )
    silent = WORK / "silent.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(silent),
        ]
    )

    srt = WORK / "captions.srt"
    write_srt(plan["narration"], duration, srt)
    final = OUT / "short.mp4"
    style = (
        "FontName=DejaVu Sans,FontSize=20,Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,"
        "Alignment=2,MarginV=260"
    )
    subtitle_filter = f"subtitles={srt.as_posix()}:force_style='{style}'"
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent),
            "-i",
            str(audio_path),
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(final),
        ]
    )
    return final


def upload_youtube(video_path: Path, plan: dict[str, Any]) -> str | None:
    client_id = os.getenv("YT_CLIENT_ID", "").strip()
    client_secret = os.getenv("YT_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("YT_REFRESH_TOKEN", "").strip()
    if not (client_id and client_secret and refresh_token):
        print("YouTube OAuth secrets are not configured; video generation succeeded, upload skipped.")
        return None

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )
    creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    description = str(plan.get("description", "")).strip()
    description += "\n\nFootage provided by Pexels: https://www.pexels.com/\n#Shorts"
    tags = [str(t)[:30] for t in (plan.get("tags") or [])][:15]
    if "shorts" not in [t.lower() for t in tags]:
        tags.append("shorts")

    body = {
        "snippet": {
            "title": str(plan.get("title", "Curiosity #Shorts"))[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": "27",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload: {int(status.progress() * 100)}%")
    video_id = response.get("id")
    print(f"Uploaded YouTube video id: {video_id}")
    return video_id


def main() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    plan = generate_plan()
    (OUT / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print("TITLE:", plan.get("title"))
    print("NARRATION WORDS:", len(str(plan.get("narration", "")).split()))

    audio = WORK / "voice.wav"
    tts(str(plan["narration"]), audio)
    final = build_video(plan, audio)
    print("VIDEO:", final)
    upload_youtube(final, plan)


if __name__ == "__main__":
    main()
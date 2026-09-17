"""Reference-video visual treatment for the KAYIP FREKANS_ serious long test.

This wrapper keeps the approved tok TTS path from mpt_long_test but prefers
licensed MOVING Pexels B-roll and longer atmospheric shots. Still images are only
a fallback. MoneyPrinterTurbo remains the final renderer. Nothing uploads to
YouTube.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps

import mpt_bridge
import mpt_long_test as base

SCENE_SECONDS = 24


def pexels_video_pool(query: str, api_key: str) -> list[dict]:
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({
        "query": query,
        "orientation": "landscape",
        "per_page": 55,
    })
    data = base.json_request(url, {
        "Authorization": api_key,
        "User-Agent": "KAYIP-FREKANS-ReviewBot/2.0",
    })
    results: list[dict] = []
    for item in data.get("videos", []):
        duration = float(item.get("duration") or 0)
        if duration < 8:
            continue
        files = [
            f for f in item.get("video_files", [])
            if f.get("file_type") == "video/mp4" and int(f.get("width") or 0) >= 1280
            and int(f.get("width") or 0) > int(f.get("height") or 0)
        ]
        if not files:
            continue
        # Prefer a 1080p-ish file rather than enormous 4K assets on GitHub runners.
        chosen = min(files, key=lambda f: abs(int(f.get("width") or 0) - 1920))
        link = chosen.get("link")
        if not link:
            continue
        user = item.get("user") or {}
        results.append({
            "kind": "video",
            "provider": "Pexels Video",
            "url": link,
            "page": item.get("url", ""),
            "credit": user.get("name", "Pexels creator"),
            "license": "Pexels License",
            "source_duration": duration,
            "width": int(chosen.get("width") or 0),
            "height": int(chosen.get("height") or 0),
        })
    return results


def atmospheric_pool(cat: str, api_key: str) -> list[dict]:
    query = base.CATEGORY_QUERIES[cat]
    if api_key:
        try:
            videos = pexels_video_pool(query, api_key)
            if len(videos) >= 3:
                return videos
        except Exception as exc:
            print(f"Pexels moving B-roll {cat} failed: {type(exc).__name__}: {exc}", flush=True)
    # Existing audited photo/Commons path is a safe fallback.
    photos = base.fetch_pool(cat, api_key)
    return [{**item, "kind": "image"} for item in photos]


def download_video(record: dict, cache: Path) -> Path:
    digest = hashlib.sha1(record["url"].encode("utf-8")).hexdigest()
    target = cache / f"{digest}.mp4"
    if target.exists():
        return target
    req = urllib.request.Request(record["url"], headers={"User-Agent": "KAYIP-FREKANS-ReviewBot/2.0"})
    with urllib.request.urlopen(req, timeout=120) as response, target.open("wb") as handle:
        total = 0
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > 120_000_000:
                raise ValueError("Pexels video asset is too large for the review runner")
            handle.write(block)
    probe = mpt_bridge.probe(target)
    if float(probe.get("seconds", 0)) < 5:
        target.unlink(missing_ok=True)
        raise ValueError("Downloaded B-roll clip is too short")
    return target


def download_scene_asset(record: dict, cache: Path, scene_dir: Path, index: int) -> Path:
    if record.get("kind") == "video":
        source = download_video(record, cache)
        target = scene_dir / f"scene-{index:04}.mp4"
        if not target.exists():
            # Re-encode to a predictable H.264/yuv420p stream and remove source audio.
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-stream_loop", "-1", "-i", str(source),
                "-t", str(SCENE_SECONDS + 1),
                "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=saturation=0.72:contrast=1.08:brightness=-0.05",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target),
            ], check=True)
        return target
    source = base.download_image(record, cache)
    target = scene_dir / f"scene-{index:04}.jpg"
    base.make_scene_image(source, target, index)
    return target


def build_visuals(tts_report: dict, output: Path) -> dict:
    duration = float(tts_report["duration_seconds"])
    chunks = tts_report["chunks"]
    scene_count = max(18, math.ceil(duration / SCENE_SECONDS))
    scene_dir = output / "scenes"
    cache = output / "source-cache"
    scene_dir.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    pools: dict[str, list[dict]] = {}
    offsets: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    credits: dict[str, dict] = {}
    scenes: list[dict] = []
    pointer = 0
    last_url = ""

    for index in range(scene_count):
        timestamp = min(duration - 0.01, index * SCENE_SECONDS)
        while pointer + 1 < len(chunks) and float(chunks[pointer]["end"]) <= timestamp:
            pointer += 1
        text = str(chunks[pointer]["text"])
        cat = base.category(text)
        if cat not in pools:
            pools[cat] = atmospheric_pool(cat, api_key)
        pool = pools[cat]
        chosen = None
        for attempt in range(len(pool) * 2):
            candidate = pool[(offsets[cat] + attempt) % len(pool)]
            if candidate["url"] != last_url and source_counts[candidate["url"]] < 2:
                chosen = candidate
                offsets[cat] += attempt + 1
                break
        if chosen is None:
            chosen = min(pool, key=lambda item: source_counts[item["url"]])
        source_counts[chosen["url"]] += 1
        last_url = chosen["url"]
        asset = download_scene_asset(chosen, cache, scene_dir, index)
        credits.setdefault(chosen["url"], chosen)
        scenes.append({
            "index": index,
            "start": round(index * SCENE_SECONDS, 3),
            "end": round(min(duration, (index + 1) * SCENE_SECONDS), 3),
            "kind": cat,
            "text_hint": text[:220],
            "asset": str(asset.resolve()),
            "media_kind": chosen.get("kind", "image"),
            "provider": chosen["provider"],
            "source_page": chosen["page"],
        })
        print(f"B-roll {index + 1}/{scene_count}: {cat} / {chosen.get('kind')}", flush=True)

    unique = len(credits)
    if unique < max(8, scene_count // 4):
        raise ValueError(f"Visual diversity too low: {unique} distinct sources for {scene_count} scenes")
    (output / "scene_assets.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "visual_credits.json").write_text(json.dumps(list(credits.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "visual_credits.txt").write_text("\n".join(
        f"{item['provider']} | {item['credit']} | {item['license']} | {item['page']}"
        for item in credits.values()
    ) + "\n", encoding="utf-8")
    moving = sum(1 for scene in scenes if scene["media_kind"] == "video")
    return {
        "scene_count": scene_count,
        "scene_seconds": SCENE_SECONDS,
        "unique_sources": unique,
        "moving_video_scenes": moving,
        "still_fallback_scenes": scene_count - moving,
        "provider_mix": dict(Counter(item["provider"] for item in credits.values())),
        "characters_shown_intentionally": False,
        "strategy": "long cinematic moving B-roll first; atmospheric story-match; no random character faces",
    }


def make_thumbnail(asset: Path, title: str, target: Path) -> None:
    source = asset
    temp = None
    if source.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
        temp = target.with_suffix(".frame.jpg")
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "2",
            "-i", str(source), "-frames:v", "1", str(temp)
        ], check=True)
        source = temp
    try:
        with Image.open(source) as image:
            image = ImageOps.fit(image.convert("RGB"), (1280, 720), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 62)
            words = title.upper().split()
            lines, current = [], ""
            for word in words:
                trial = (current + " " + word).strip()
                if current and draw.textbbox((0, 0), trial, font=font)[2] > 1030:
                    lines.append(current); current = word
                else:
                    current = trial
            if current:
                lines.append(current)
            y = 430 - max(0, len(lines[:3]) - 1) * 38
            for line in lines[:3]:
                draw.text((70, y), line, font=font, fill="white", stroke_width=5, stroke_fill="black")
                y += 76
            image.save(target, quality=94)
    finally:
        if temp:
            temp.unlink(missing_ok=True)


def render_with_mpt(workspace: Path, upstream: Path, output: Path) -> dict:
    workspace = workspace.resolve()
    upstream = upstream.resolve(strict=True)
    if upstream != (workspace / "upstream" / "MoneyPrinterTurbo").resolve():
        raise ValueError("Unexpected MoneyPrinterTurbo path")
    commit = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if commit != mpt_bridge.UPSTREAM_COMMIT or not (upstream / "LICENSE").is_file():
        raise ValueError("Unreviewed MoneyPrinterTurbo revision")

    state = json.loads((output / "story_state.json").read_text(encoding="utf-8"))
    tts = json.loads((output / "tts_report.json").read_text(encoding="utf-8"))
    scenes = json.loads((output / "scene_assets.json").read_text(encoding="utf-8"))
    script = (output / "narration_script.txt").read_text(encoding="utf-8-sig").strip()
    narration = (output / "narration.wav").resolve(strict=True)
    assets = [str(Path(item["asset"]).resolve(strict=True)) for item in scenes]
    if len(assets) < 18:
        raise ValueError("Insufficient cinematic scene assets for long render")

    command = [
        sys.executable, str(upstream / "cli.py"),
        "--video-subject", "KAYIP FREKANS_ uzun cinli paranormal hikaye",
        "--video-script", script,
        "--video-language", "tr-TR",
        "--voice-name", "no-voice",
        "--custom-audio-file", str(narration),
        "--video-source", "local",
        "--video-materials", ",".join(assets),
        "--video-aspect", "16:9",
        "--video-fit-mode", "cover",
        "--video-concat-mode", "sequential",
        "--video-transition-mode", "FadeIn",
        "--video-clip-duration", str(SCENE_SECONDS),
        "--video-count", "1",
        "--bgm-type", "none",
        "--no-subtitle-enabled",
        "--stop-at", "video",
    ]
    subprocess.run(command, cwd=upstream, check=True)
    candidates = sorted((upstream / "storage" / "tasks").rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    wanted = float(tts["duration_seconds"])
    base_video = None
    for candidate in candidates:
        try:
            data = mpt_bridge.probe(candidate)
        except Exception:
            continue
        kinds = {stream.get("codec_type") for stream in data.get("streams", [])}
        if {"video", "audio"} <= kinds and abs(float(data["seconds"]) - wanted) <= 8:
            base_video = candidate
            break
    if base_video is None:
        raise RuntimeError("MoneyPrinterTurbo did not produce a duration-matched long MP4")

    final = output / "KAYIP_FREKANS_MPT_UZUN_TEST.mp4"
    caption = (output / "captions.srt").resolve(strict=True).as_posix().replace("'", "\\'")
    fade_out_start = max(1.0, wanted - 2.0)
    filters = (
        f"[0:v]subtitles='{caption}':force_style='FontName=DejaVu Sans,FontSize=28,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=34'[v];"
        "[0:a]volume=1.0[voice];"
        f"[1:a]afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d=2,volume=0.32[bed];"
        "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]"
    )
    ambience = f"aevalsrc=0.008*sin(2*PI*48*t)+0.004*sin(2*PI*72*t):s=24000:d={wanted:.3f}"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(base_video), "-f", "lavfi", "-i", ambience,
        "-filter_complex", filters, "-map", "[v]", "-map", "[a]",
        "-t", f"{wanted:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)
    ], check=True)
    final_seconds = base.probe_seconds(final)
    if abs(final_seconds - wanted) > 1.0:
        raise ValueError("Final post-processed video duration does not match tok narration")

    thumbnail = output / "thumbnail.jpg"
    make_thumbnail(Path(scenes[0]["asset"]), str(state["title"]), thumbnail)
    moving = sum(1 for scene in scenes if scene.get("media_kind") == "video")
    report = {
        "engine": "MoneyPrinterTurbo",
        "upstream_commit": commit,
        "title": state["title"],
        "target_minutes": state["target_minutes"],
        "actual_video_minutes": round(final_seconds / 60, 2),
        "voice": "serkan-v6-2-tok long review candidate",
        "full_narration_user_approved": False,
        "scene_count": len(scenes),
        "moving_video_scenes": moving,
        "visual_reference_mode": "long dark cinematic B-roll with FadeIn transitions",
        "subtitles": "chunk-timed Turkish SRT burned after MPT render",
        "background_audio": "very-low local ambience; narrator remains dominant",
        "output": str(final.relative_to(workspace)),
        "thumbnail": str(thumbnail.relative_to(workspace)),
        "youtube_uploaded": False,
        "publication_allowed": False,
        "human_review_required": True,
    }
    (output / "final_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return report


def prepare(workspace: Path, approved_audio: Path, target_minutes: int) -> dict:
    output = workspace.resolve() / "output" / "long-test"
    script = output / "narration_script.txt"
    if not script.is_file():
        raise FileNotFoundError("Long story narration script is missing")
    tts = base.generate_tok_narration(script, approved_audio, output, target_minutes)
    visuals = build_visuals(tts, output)
    report = {"tts": {k: v for k, v in tts.items() if k != "chunks"}, "visuals": visuals}
    (output / "prepare_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=["prepare", "render"], required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--approved-audio", type=Path)
    p.add_argument("--upstream", type=Path)
    p.add_argument("--target-minutes", type=int, default=15)
    args = p.parse_args()
    workspace = args.workspace.resolve()
    if args.stage == "prepare":
        if not args.approved_audio:
            raise ValueError("--approved-audio is required for prepare")
        prepare(workspace, args.approved_audio, args.target_minutes)
    else:
        if not args.upstream:
            raise ValueError("--upstream is required for render")
        render_with_mpt(workspace, args.upstream, workspace / "output" / "long-test")

"""Serious review-only KAYIP FREKANS_ long video test.

Stages:
  prepare  - extend the SHA-pinned user-approved tok audition with local
             Chatterbox TTS, build timed captions and story-matched atmosphere
             visuals from Pexels (or Wikimedia Commons fallback).
  render   - use the audited MoneyPrinterTurbo commit as the video renderer,
             then add our known caption timings and a very low local ambience.

Nothing in this file uploads to YouTube. The generated full narration is a
REVIEW candidate, not automatically user-approved for publication.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

import bot
import mpt_bridge

APPROVED_TOK_SHA256 = "586244cd639faf5fd5995d1f4a9e74c4bceb7a88852075eee8d046274ea9528b"
SCENE_SECONDS = 12
W, H = 1920, 1080

CATEGORY_QUERIES = {
    "door": "old wooden door dark night",
    "corridor": "dark empty corridor abandoned",
    "room": "dark empty room old house",
    "house": "old rural house night",
    "forest": "foggy dark forest path",
    "stairs": "old staircase dark interior",
    "window": "dark window rain night",
    "candle": "candle dark room",
    "road": "empty village road night",
    "basement": "old basement cellar dark",
}

CATEGORY_WORDS = {
    "door": ("kapı", "kilit", "tokmak", "eşik"),
    "corridor": ("koridor", "hol", "duvar", "tavan"),
    "room": ("oda", "yatak", "salon", "mutfak"),
    "house": ("ev", "köy", "bahçe", "çatı", "avlu"),
    "forest": ("orman", "ağaç", "patika", "çalılık"),
    "stairs": ("merdiven", "basamak"),
    "window": ("pencere", "cam", "perde"),
    "candle": ("mum", "alev", "kibrit"),
    "road": ("yol", "sokak", "patika", "araba"),
    "basement": ("bodrum", "kiler", "mahzen"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def probe_seconds(path: Path) -> float:
    value = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)
    ], text=True).strip()
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"Invalid media duration: {path}")
    return value


def split_tts(text: str, max_chars: int = 480) -> list[str]:
    sentences = bot.sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        if len(sentence) > max_chars:
            words = sentence.split()
            piece: list[str] = []
            for word in words:
                trial = " ".join(piece + [word])
                if piece and len(trial) > max_chars:
                    if current:
                        chunks.append(" ".join(current)); current = []
                    chunks.append(" ".join(piece))
                    piece = [word]
                else:
                    piece.append(word)
            if piece:
                if current:
                    chunks.append(" ".join(current)); current = []
                chunks.append(" ".join(piece))
            continue
        trial = " ".join(current + [sentence])
        if current and len(trial) > max_chars:
            chunks.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        chunks.append(" ".join(current))
    return [chunk.strip() for chunk in chunks if len(chunk.split()) >= 3]


def srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    h, rem = divmod(milliseconds, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def subtitle_groups(text: str, max_words: int = 9) -> list[str]:
    groups: list[str] = []
    for sentence in bot.sentences(text):
        words = sentence.split()
        for i in range(0, len(words), max_words):
            groups.append(" ".join(words[i:i + max_words]))
    return [g for g in groups if g]


def generate_tok_narration(script: Path, approved_audio: Path, output: Path, target_minutes: int) -> dict:
    approved_audio = approved_audio.resolve(strict=True)
    if sha256(approved_audio) != APPROVED_TOK_SHA256:
        raise ValueError("Tok audition does not match the user-approved SHA; no fallback voice")
    output.mkdir(parents=True, exist_ok=True)
    prompt = output / "tok-reference-window.wav"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(approved_audio), "-t", "10",
        "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(prompt)
    ], check=True)

    text = script.read_text(encoding="utf-8-sig").strip()
    chunks = split_tts(text)
    if len(chunks) < 12:
        raise ValueError("Long narration unexpectedly contains too few TTS chunks")

    try:
        import numpy as np
        import soundfile as sf
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except ImportError as exc:
        raise RuntimeError("Long tok narration requires chatterbox-tts, torch and soundfile") from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    sample_rate = int(model.sr)
    silence = np.zeros(int(sample_rate * 0.16), dtype=np.float32)
    rendered: list[object] = []
    timing: list[dict] = []
    cursor = 0.0
    for index, chunk in enumerate(chunks):
        torch.manual_seed(2026 + index)
        wav = model.generate(
            chunk,
            language_id="tr",
            audio_prompt_path=str(prompt),
            exaggeration=0.55,
            cfg_weight=0.30,
        )
        audio = wav.detach().cpu().numpy().reshape(-1).astype("float32")
        if len(audio) < sample_rate or not np.isfinite(audio).all():
            raise ValueError(f"Tok TTS chunk {index + 1} is empty or non-finite")
        peak = float(np.max(np.abs(audio)))
        if peak <= 0.001:
            raise ValueError(f"Tok TTS chunk {index + 1} is silent")
        if peak > 0.96:
            audio = audio * (0.92 / peak)
        seconds = len(audio) / sample_rate
        timing.append({
            "index": index + 1,
            "start": round(cursor, 3),
            "end": round(cursor + seconds, 3),
            "seconds": round(seconds, 3),
            "text": chunk,
        })
        rendered.append(audio)
        rendered.append(silence)
        cursor += seconds + len(silence) / sample_rate
        print(f"Tok anlatim {index + 1}/{len(chunks)} - {cursor / 60:.1f} dk", flush=True)

    full = np.concatenate(rendered[:-1])
    narration = output / "narration.wav"
    sf.write(str(narration), full, sample_rate, subtype="PCM_16")
    seconds = probe_seconds(narration)
    lower = max(720, target_minutes * 60 * 0.80)
    upper = target_minutes * 60 * 1.40
    if not lower <= seconds <= upper:
        raise ValueError(
            f"Generated long tok narration is {seconds:.1f}s; expected {lower:.0f}-{upper:.0f}s"
        )

    entries: list[str] = []
    cue = 1
    for item in timing:
        groups = subtitle_groups(item["text"])
        if not groups:
            continue
        weights = [max(1, len(group.split())) for group in groups]
        total_weight = sum(weights)
        start = float(item["start"])
        span = max(0.5, float(item["end"]) - start)
        consumed = 0.0
        for group, weight in zip(groups, weights):
            duration = span * weight / total_weight
            end = min(float(item["end"]), start + duration)
            entries.append(f"{cue}\n{srt_time(start)} --> {srt_time(end)}\n{group}\n")
            cue += 1
            start = end
            consumed += duration
    (output / "captions.srt").write_text("\n".join(entries) + "\n", encoding="utf-8")
    report = {
        "engine": "ChatterboxMultilingualTTS 0.1.7",
        "voice": "serkan-v6-2-tok review candidate",
        "source_audition_sha256": APPROVED_TOK_SHA256,
        "prompt_seconds_used": 10,
        "chunk_count": len(timing),
        "duration_seconds": round(seconds, 3),
        "duration_minutes": round(seconds / 60, 2),
        "full_narration_user_approved": False,
        "fallback_voice_used": False,
        "youtube_uploaded": False,
        "chunks": timing,
    }
    (output / "tts_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt.unlink(missing_ok=True)
    return report


def category(text: str) -> str:
    low = text.casefold()
    scores = {key: sum(low.count(word) for word in words) for key, words in CATEGORY_WORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "corridor"


def json_request(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "KAYIP-FREKANS-ReviewBot/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def pexels_pool(query: str, api_key: str) -> list[dict]:
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode({
        "query": query, "orientation": "landscape", "per_page": 80,
    })
    data = json_request(url, {"Authorization": api_key, "User-Agent": "KAYIP-FREKANS-ReviewBot/1.0"})
    results = []
    for item in data.get("photos", []):
        if item.get("width", 0) < 1280 or item.get("width", 0) <= item.get("height", 0):
            continue
        alt = str(item.get("alt") or "")
        if re.search(r"\b(man|woman|people|person|portrait|girl|boy|child|couple)\b", alt, re.I):
            continue
        src = item.get("src", {}).get("large2x") or item.get("src", {}).get("large")
        if not src:
            continue
        results.append({
            "provider": "Pexels", "url": src, "page": item.get("url", ""),
            "credit": item.get("photographer", "Pexels"), "license": "Pexels License",
        })
    return results


def commons_pool(query: str) -> list[dict]:
    params = {
        "action": "query", "generator": "search", "gsrsearch": query,
        "gsrnamespace": "6", "gsrlimit": "35", "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": "2200", "format": "json",
    }
    data = json_request("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    results = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        title = str(page.get("title") or "")
        if not url or not re.search(r"\.(jpe?g|png)(?:\?|$)", url, re.I):
            continue
        meta = info.get("extmetadata", {})
        license_name = strip_html(meta.get("LicenseShortName", {}).get("value", "Wikimedia Commons"))
        artist = strip_html(meta.get("Artist", {}).get("value", "Wikimedia Commons contributor"))
        results.append({
            "provider": "Wikimedia Commons", "url": url,
            "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "credit": artist[:180], "license": license_name[:120],
        })
    return results


def fetch_pool(cat: str, api_key: str) -> list[dict]:
    query = CATEGORY_QUERIES[cat]
    if api_key:
        try:
            pool = pexels_pool(query, api_key)
            if len(pool) >= 4:
                return pool
        except Exception as exc:
            print(f"Pexels {cat} failed, Commons fallback: {exc}", flush=True)
    pool = commons_pool(query)
    if len(pool) < 3:
        raise RuntimeError(f"No sufficiently varied licensed visual pool for {cat}")
    return pool


def download_image(record: dict, cache: Path) -> Path:
    digest = hashlib.sha1(record["url"].encode("utf-8")).hexdigest()
    path = cache / f"{digest}.jpg"
    if path.exists():
        return path
    req = urllib.request.Request(record["url"], headers={"User-Agent": "KAYIP-FREKANS-ReviewBot/1.0"})
    with urllib.request.urlopen(req, timeout=90) as response:
        data = response.read(18_000_000)
    raw = cache / f"{digest}.download"
    raw.write_bytes(data)
    try:
        with Image.open(raw) as image:
            image = image.convert("RGB")
            if image.width < 1100 or image.height < 600:
                raise ValueError("source image resolution too low")
            image.save(path, quality=94)
    finally:
        raw.unlink(missing_ok=True)
    return path


def make_scene_image(source: Path, target: Path, index: int) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        cx = min(0.62, max(0.38, 0.5 + math.sin(index * 0.91) * 0.08))
        cy = min(0.58, max(0.42, 0.5 + math.cos(index * 0.73) * 0.04))
        image = ImageOps.fit(image, (W, H), Image.Resampling.LANCZOS, centering=(cx, cy))
        image = ImageEnhance.Color(image).enhance(0.50)
        image = ImageEnhance.Contrast(image).enhance(1.16)
        image = ImageEnhance.Brightness(image).enhance(0.72)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(int(H * 0.64), H):
            alpha = int(120 * (y - H * 0.64) / (H * 0.36))
            draw.line((0, y, W, y), fill=(0, 0, 0, alpha))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        image.save(target, quality=93, subsampling=0)


def build_visuals(tts_report: dict, output: Path) -> dict:
    duration = float(tts_report["duration_seconds"])
    chunks = tts_report["chunks"]
    scene_count = max(20, math.ceil(duration / SCENE_SECONDS))
    scene_dir = output / "scenes"
    cache = output / "source-cache"
    scene_dir.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    pools: dict[str, list[dict]] = {}
    offsets: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    credits: dict[str, dict] = {}
    scenes = []
    pointer = 0
    last_url = ""

    for index in range(scene_count):
        timestamp = min(duration - 0.01, index * SCENE_SECONDS)
        while pointer + 1 < len(chunks) and float(chunks[pointer]["end"]) <= timestamp:
            pointer += 1
        text = str(chunks[pointer]["text"])
        cat = category(text)
        if cat not in pools:
            pools[cat] = fetch_pool(cat, api_key)
        pool = pools[cat]
        chosen = None
        for attempt in range(len(pool) * 2):
            candidate = pool[(offsets[cat] + attempt) % len(pool)]
            if candidate["url"] != last_url and source_counts[candidate["url"]] < 3:
                chosen = candidate
                offsets[cat] += attempt + 1
                break
        if chosen is None:
            fallback = "corridor" if cat != "corridor" else "house"
            if fallback not in pools:
                pools[fallback] = fetch_pool(fallback, api_key)
            pool = pools[fallback]
            chosen = min(pool, key=lambda item: source_counts[item["url"]])
            cat = fallback
        source_counts[chosen["url"]] += 1
        last_url = chosen["url"]
        source = download_image(chosen, cache)
        target = scene_dir / f"scene-{index:04}.jpg"
        make_scene_image(source, target, index)
        credits.setdefault(chosen["url"], chosen)
        scenes.append({
            "index": index, "start": round(index * SCENE_SECONDS, 3),
            "end": round(min(duration, (index + 1) * SCENE_SECONDS), 3),
            "kind": cat, "text_hint": text[:220], "asset": str(target.resolve()),
            "provider": chosen["provider"], "source_page": chosen["page"],
        })
        print(f"Gorsel {index + 1}/{scene_count}: {cat}", flush=True)

    if len(credits) < 10:
        raise ValueError(f"Visual diversity too low: only {len(credits)} distinct source images")
    (output / "scene_assets.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "visual_credits.json").write_text(json.dumps(list(credits.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "visual_credits.txt").write_text("\n".join(
        f"{item['provider']} | {item['credit']} | {item['license']} | {item['page']}"
        for item in credits.values()
    ) + "\n", encoding="utf-8")
    return {
        "scene_count": scene_count, "unique_source_images": len(credits),
        "provider_mix": dict(Counter(item["provider"] for item in credits.values())),
        "characters_shown_intentionally": False,
        "strategy": "story-matched atmospheric locations/objects; avoids random changing character faces",
    }


def make_thumbnail(scene: Path, title: str, target: Path) -> None:
    with Image.open(scene) as image:
        image = ImageOps.fit(image.convert("RGB"), (1280, 720), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(image)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, 62)
        words = title.upper().split()
        lines: list[str] = []
        current = ""
        for word in words:
            trial = (current + " " + word).strip()
            if current and draw.textbbox((0, 0), trial, font=font)[2] > 1030:
                lines.append(current); current = word
            else:
                current = trial
        if current:
            lines.append(current)
        lines = lines[:3]
        y = 430 - max(0, len(lines) - 1) * 38
        for line in lines:
            draw.text((70, y), line, font=font, fill="white", stroke_width=5, stroke_fill="black")
            y += 76
        image.save(target, quality=94)


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
    if len(assets) < 20:
        raise ValueError("Insufficient scene assets for long render")

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
        "--video-transition-mode", "none",
        "--video-clip-duration", str(SCENE_SECONDS),
        "--video-count", "1",
        "--bgm-type", "none",
        "--no-subtitle-enabled",
        "--stop-at", "video",
    ]
    subprocess.run(command, cwd=upstream, check=True)
    candidates = sorted((upstream / "storage" / "tasks").rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    wanted = float(tts["duration_seconds"])
    base = None
    for candidate in candidates:
        try:
            data = mpt_bridge.probe(candidate)
        except Exception:
            continue
        kinds = {stream.get("codec_type") for stream in data.get("streams", [])}
        if {"video", "audio"} <= kinds and abs(float(data["seconds"]) - wanted) <= 6:
            base = candidate
            break
    if base is None:
        raise RuntimeError("MoneyPrinterTurbo did not produce a duration-matched long MP4")

    final = output / "KAYIP_FREKANS_MPT_UZUN_TEST.mp4"
    caption = (output / "captions.srt").resolve(strict=True).as_posix().replace("'", "\\'")
    fade_out_start = max(1.0, wanted - 2.0)
    filters = (
        f"[0:v]subtitles='{caption}':force_style='FontName=DejaVu Sans,FontSize=28,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=34'[v];"
        "[0:a]volume=1.0[voice];"
        f"[1:a]afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d=2,volume=0.40[bed];"
        "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]"
    )
    ambience = f"aevalsrc=0.010*sin(2*PI*48*t)+0.006*sin(2*PI*72*t):s=24000:d={wanted:.3f}"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(base), "-f", "lavfi", "-i", ambience,
        "-filter_complex", filters, "-map", "[v]", "-map", "[a]",
        "-t", f"{wanted:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)
    ], check=True)
    final_seconds = probe_seconds(final)
    if abs(final_seconds - wanted) > 1.0:
        raise ValueError("Final post-processed video duration does not match tok narration")

    thumbnail = output / "thumbnail.jpg"
    make_thumbnail(Path(scenes[0]["asset"]), str(state["title"]), thumbnail)
    report = {
        "engine": "MoneyPrinterTurbo",
        "upstream_commit": commit,
        "title": state["title"],
        "target_minutes": state["target_minutes"],
        "actual_video_minutes": round(final_seconds / 60, 2),
        "voice": "serkan-v6-2-tok long review candidate",
        "full_narration_user_approved": False,
        "scene_count": len(scenes),
        "subtitles": "chunk-timed Turkish SRT burned after MPT render",
        "background_audio": "local low-volume synthetic ambience; no downloaded music",
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
    tts = generate_tok_narration(script, approved_audio, output, target_minutes)
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

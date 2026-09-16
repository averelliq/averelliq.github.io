"""One-off, upload-free production of three manually fact-checked English Shorts.

This is not the daily automatic workflow. It deliberately uses one subject per
stock search, retains provenance, and never uploads. Publishing is a separate
step after examining the rendered MP4s.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import requests

import main as bot

TOPICS = {
    "water": {
        "title": "Why Water Beads Up Into Drops #Shorts",
        "description": "Why do tiny drops hold together? Here's a simple look at surface tension.",
        "tags": ["shorts", "science", "water", "surface tension", "curiosity"],
        "narration": (
            "Why does water gather into tiny rounded drops? "
            "Water molecules attract their neighbors. At the surface, that attraction "
            "creates surface tension, which tends to reduce the exposed area. "
            "That's why small drops often look rounded in the air or on a water-repelling surface. "
            "But a drop resting on glass may spread out instead. "
            "Gravity, the surface underneath, and the balance of attraction all change its shape. "
            "The next time you spot a bead of water, you're seeing these forces at work."
        ),
        "queries": ["water droplet macro", "water drops on glass", "water droplets leaf"],
    },
    "cats": {
        "title": "Why Cats Knead Your Blanket #Shorts",
        "description": "Those tiny paw presses begin early in life. Here are two possible reasons adult cats keep kneading.",
        "tags": ["shorts", "cats", "cat behavior", "animals", "curiosity"],
        "narration": (
            "Why does your cat press its paws into your blanket? "
            "Kittens knead while nursing, and many cats keep the movement as adults. "
            "A soft blanket may feel comforting, but that's not the only possible reason. "
            "Cats also have scent glands in their paw pads, so kneading may leave their scent behind. "
            "Some cats knead often, and others hardly ever do. "
            "We can't know exactly what every cat is thinking, but those gentle paw presses can have a surprisingly long history."
        ),
        "queries": ["cat kneading blanket", "cat paws blanket", "cat on soft blanket"],
    },
    "candle": {
        "title": "Why Candle Flames Dance #Shorts",
        "description": "Even tiny movements of air can make a flame flicker. Watch how the moving air changes its shape.",
        "tags": ["shorts", "candle", "flame", "everyday science", "curiosity"],
        "narration": (
            "Ever notice a candle flame dancing in a quiet room? "
            "The wax melts and travels up the wick, where vaporized fuel burns. "
            "Hot gases rise, while surrounding air brings in oxygen. "
            "Even a faint draft can bend the flame as the air moves. "
            "A nearby window, a passing hand, or rising warm air can all change its shape. "
            "So when a candle flickers, you may be watching an invisible current reveal itself in light. "
            "It's a tiny window into moving air."
        ),
        "queries": ["candle flame close up", "candle flame flickering", "burning candle dark"],
    },
}


def sh(args: list[str]) -> None:
    subprocess.run(args, check=True)


def find_stock(query: str, used: set[int], dest: Path) -> dict:
    if not bot.PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY absent")
    r = requests.get(
        "https://api.pexels.com/v1/videos/search",
        headers={"Authorization": bot.PEXELS_API_KEY},
        params={"query": query, "orientation": "portrait", "per_page": 15}, timeout=45,
    )
    r.raise_for_status()
    for video in r.json().get("videos", []):
        video_id = video.get("id")
        if not isinstance(video_id, int) or video_id in used:
            continue
        variants = sorted((f for f in video.get("video_files", [])
                           if f.get("link", "").startswith("https://")
                           and int(f.get("height") or 0) > int(f.get("width") or 0)
                           and int(f.get("height") or 0) >= 720
                           and int(f.get("width") or 0) >= 360),
                          key=lambda f: abs(int(f.get("height") or 0) - 1280))
        for variant in variants[:2]:
            try:
                total = 0
                with requests.get(variant["link"], timeout=90, stream=True) as response:
                    response.raise_for_status()
                    with dest.open("wb") as output:
                        for chunk in response.iter_content(1024 * 1024):
                            total += len(chunk)
                            if total > 35 * 1024 * 1024:
                                raise ValueError("Stock too large")
                            output.write(chunk)
                if float(bot.ffprobe_duration(dest)) >= 2:
                    used.add(video_id)
                    return {"pexels_id": video_id, "query": query,
                            "duration": bot.ffprobe_duration(dest),
                            "source_page": video.get("url", "")}
            except (requests.RequestException, ValueError, OSError, subprocess.CalledProcessError):
                dest.unlink(missing_ok=True)
    raise RuntimeError("No usable subject footage for " + query)


def produce(slug: str) -> None:
    if slug not in TOPICS:
        raise ValueError("Unknown story slug")
    data = TOPICS[slug]
    root = Path(__file__).resolve().parent
    out = root / "reviewed" / slug
    out.mkdir(parents=True, exist_ok=True)
    voice = out / "voice.wav"
    bot.tts(data["narration"], voice)
    duration = bot.ffprobe_duration(voice)
    if not 23 <= duration <= 65:
        raise RuntimeError(f"Unexpected narration duration: {duration:.1f}s")
    used: set[int] = set()
    sources = []
    for idx, query in enumerate(data["queries"]):
        path = out / f"stock_{idx}.mp4"
        detail = find_stock(query, used, path)
        sources.append(detail)
    clips = []
    count = 8
    seconds = duration / count
    for idx in range(count):
        source = out / f"stock_{idx % len(sources)}.mp4"
        clip = out / f"scene_{idx}.mp4"
        sh(["ffmpeg", "-nostdin", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(source),
            "-t", f"{seconds:.3f}", "-an", "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p", str(clip)])
        clips.append(clip)
    listing = out / "concat.txt"
    listing.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    silent = out / "silent.mp4"
    sh(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", str(listing), "-c", "copy", str(silent)])
    srt = out / "captions.srt"
    bot.write_srt(data["narration"], duration, srt)
    final = out / "short.mp4"
    filter_string = (
        f"subtitles={srt}:force_style='FontName=DejaVu Sans,FontSize=12,Bold=1,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
        "Outline=3,Shadow=1,Alignment=2,MarginV=115'"
    )
    sh(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(silent), "-i", str(voice),
        "-vf", filter_string, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(final)])
    plan = {**{k: data[k] for k in ("title", "description", "tags", "narration")},
            "topic": slug, "stock_sources": sources, "review_status": "NEEDS_HUMAN_REVIEW",
            "uploaded": False}
    (out / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    result = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration,size",
        "-show_entries", "stream=codec_type,width,height", "-of", "json", str(final)], text=True))
    print("FINISHED_UNPUBLISHED", slug, json.dumps(result), flush=True)


if __name__ == "__main__":
    produce(sys.argv[1])

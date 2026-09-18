"""Single live-action science Short; five independent storm clips or no upload.

This file is triggered only by the separately named one-off workflow. Never re-run
its workflow after YouTube may have received a video.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import requests

import live_action_guard
import montage_fx
import quality_entry as quality
import safe_captions
import selection_guard
import upgrade

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "one_lightning_work_20260918"
OUT = ROOT / "one_lightning_output_20260918"

PLAN = {
    "slug": "lightning_air_hotter_than_sun_surface",
    "topic": "real lightning heating air hotter than the Sun's surface and causing thunder",
    "theme": "science",
    "title": "Lightning Heats Air HOTTER Than the Sun's Surface?! #Shorts",
    "description": (
        "Lightning can briefly heat the air it passes through to about 50,000°F — "
        "roughly five times hotter than the Sun's surface. Rapidly expanding "
        "air creates thunder. Actual filmed lightning, not cartoons. "
        "Sources: NOAA National Severe Storms Laboratory and National Weather Service. "
        "https://www.nssl.noaa.gov/education/svrwx101/lightning/ "
        "https://www.weather.gov/safety/lightning-temperature "
        "#Shorts #Lightning #ScienceFacts #Thunder"
    ),
    "tags": ["shorts", "lightning", "thunder", "science facts", "weather", "storms"],
    "scenes": [
        {
            "voiceover": "Lightning can heat air hotter than the Sun's surface. Yes, the air around one flash.",
            "query": "lightning bolt storm night",
            "backup_queries": ["lightning strike night sky", "lightning flash sky"],
            "caption": "Hotter than the Sun's surface?",
        },
        {
            "voiceover": "A lightning bolt sends electric current through air. It can reach fifty thousand degrees Fahrenheit.",
            "query": "lightning strike night sky",
            "backup_queries": ["lightning bolts night sky", "lightning storm timelapse"],
            "caption": "50,000 degrees Fahrenheit",
        },
        {
            "voiceover": "That sudden heat makes the surrounding air expand incredibly fast. It creates a powerful pressure wave.",            
            "query": "lightning thunderstorm clouds",
            "backup_queries": ["thunderstorm lightning horizon", "lightning storm clouds"],
            "caption": "Superheated air expands",
        },
        {
            "voiceover": "The pressure wave travels outward from the flash. When it reaches your ears, you hear thunder.",            
            "query": "lightning over city",
            "backup_queries": ["lightning storm timelapse", "lightning flashes sky"],
            "caption": "That's the sound of thunder",
        },
        {
            "voiceover": "You see the flash before hearing its sound because light travels faster. Hear thunder? Get indoors.",            
            "query": "thunderstorm lightning horizon",
            "backup_queries": ["lightning bolt storm night", "lightning storm clouds"],
            "caption": "See flash. Hear thunder. Get indoors.",
        },
    ],
}


def validate() -> None:
    scenes = PLAN["scenes"]
    word_count = sum(len(scene["voiceover"].split()) for scene in scenes)
    if len(scenes) != 5 or not 65 <= word_count <= 95:
        raise ValueError(f"Expected five concise scenes; got {word_count} words")
    if len(PLAN["title"]) > 70 or "#Shorts" not in PLAN["title"]:
        raise ValueError("Short title invalid")
    if len({scene["query"] for scene in scenes}) != 5:
        raise ValueError("Each scene needs a unique first footage query")
    if any(len(scene["backup_queries"]) != 2 for scene in scenes):
        raise ValueError("Every scene requires two filmed-footage alternatives")
    for scene in scenes:
        if any(term in scene["query"].lower() for term in ("animation", "infographic", "illustration")):
            raise ValueError("No illustrations or diagrams in stock requests")
        for cue in safe_captions.cues(scene["voiceover"].split()):
            if len(" ".join(cue)) > safe_captions.MAX_CHARS:
                raise ValueError("Phone caption line overflow")
    PLAN["narration"] = " ".join(scene["voiceover"] for scene in scenes)
    print(f"SCRIPT VERIFIED: {word_count} words, 5 distinct scene queries, safe captions",flush=True)


def preflight() -> None:
    key = upgrade.bot.PEXELS_API_KEY
    if not key:
        raise RuntimeError("Pexels API key absent; no upload")
    distinct: set[int] = set()
    for number, scene in enumerate(PLAN["scenes"], 1):
        scene_ids: set[int] = set()
        for query in [scene["query"], *scene["backup_queries"]]:
            response = requests.get("https://api.pexels.com/v1/videos/search",
                                    headers={"Authorization":key},
                                    params={"query":query,"orientation":"portrait","per_page":25,
                                            "page":1,"locale":"en-US"},timeout=45)
            response.raise_for_status()
            for item in response.json().get("videos",[]):
                slug = item.get("url", "").rstrip("/").split("/")[-1].lower()
                if (type(item.get("id")) is int and
                        ("lightning" in slug or "thunderstorm" in slug) and
                        not any(term in slug for term in ("animation", "illustration", "cartoon", "cgi")) and
                        selection_guard._file_options(item)):
                    scene_ids.add(item["id"])
            if len(scene_ids) >= 5:
                break
        print(f"PREFLIGHT filmed lightning candidates for scene {number}: {len(scene_ids)}",flush=True)
        if len(scene_ids) < 3:
            raise RuntimeError(f"Too few actual lightning assets for scene {number}; no upload")
        distinct.update(scene_ids)
    if len(distinct) < 5:
        raise RuntimeError("Fewer than five distinct lightning source IDs; no upload")
    print(f"PREFLIGHT PASSED: {len(distinct)} candidate lightning source IDs",flush=True)


def main() -> None:
    validate()
    if (os.getenv("YOUTUBE_PRIVACY") != "public" or
            os.getenv("SHORTS_SKIP_UPLOAD") != "0" or
            os.getenv("GITHUB_RUN_ATTEMPT", "1") != "1"):
        raise RuntimeError("One authorized public upload only; no automatic retries")
    if WORK.exists() or OUT.exists():
        raise RuntimeError("Existing output detected; do not risk duplicate upload")
    preflight()
    live_action_guard.install()
    safe_captions.install()
    state = montage_fx.install(quality)
    bot = upgrade.bot
    bot.WORK = WORK
    bot.OUT = OUT
    WORK.mkdir(parents=True, exist_ok=False)
    OUT.mkdir(parents=True, exist_ok=False)
    upgrade.CURRENT_PLAN = PLAN
    voice = WORK / "voice.wav"
    upgrade.scene_tts(PLAN["narration"], voice)
    video = quality.checked_build(PLAN, voice)
    scenes = PLAN["scenes"]
    if (not PLAN.get("visual_review",{}).get("approved") or
            not PLAN.get("live_action_review",{}).get("approved") or
            len({scene.get("pexels_video_id") for scene in scenes}) != 5):
        raise RuntimeError("Five unique, independently approved real-video scenes required")
    if not state["animated_captions"] or not state["original_music"] or state["motion_clips"] != 5:
        raise RuntimeError("Animated captions, original music or montage effects missing")
    captions_file = WORK / "captions.ass"
    caption_lines = [line for line in captions_file.read_text(encoding="utf8").splitlines()
                     if line.startswith("Dialogue:")]
    if len(caption_lines) < 20:
        raise RuntimeError("Phone-caption timing too sparse")
    for line in caption_lines:
        text = re.sub(r"\{[^}]*\}","",line.split(",",9)[-1])
        if len(text)>safe_captions.MAX_CHARS:
            raise RuntimeError("Phone caption would overflow")
    source_path = OUT / "visual_sources.json"
    sources = json.loads(source_path.read_text(encoding="utf8"))
    if not isinstance(sources,list) or len(sources)!=5:
        raise RuntimeError("Stock footage provenance is incomplete")
    for item in sources:
        item["visuals_are_stock_illustrations"] = False
        item["visual_type"] = "filmed_stock_footage"
    source_path.write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding="utf8")
    PLAN["source_reading"] = [
        "https://www.nssl.noaa.gov/education/svrwx101/lightning/",
        "https://www.weather.gov/safety/lightning-temperature",
    ]
    (OUT / "plan.json").write_text(json.dumps(PLAN,ensure_ascii=False,indent=2),encoding="utf8")
    print("READY VERIFIED LIGHTNING SHORT:", PLAN["quality_checks"],
          "sha256",hashlib.sha256(video.read_bytes()).hexdigest()[:16],flush=True)
    video_id = bot.upload_youtube(video, {k:PLAN[k] for k in ("title","description","tags")})
    if not isinstance(video_id,str) or len(video_id)<6:
        raise RuntimeError("YouTube upload returned no usable ID; do not retry")
    print(f"PUBLISHED ONE REAL LIGHTNING SHORT: https://www.youtube.com/shorts/{video_id}",flush=True)


if __name__ == "__main__":
    main()

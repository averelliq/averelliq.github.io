"""Exactly one original curiosity Short; verify live-action scenes before public upload.

One-shot workflow only; never rerun after an uncertain/partial upload.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import requests

import live_action_guard
import montage_fx
import quality_entry as quality
import safe_captions
import selection_guard
import upgrade

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "one_octopus_work_20260918"
OUT = ROOT / "one_octopus_output_20260918"

PLAN = {
    "slug": "octopus_three_hearts_blue_blood",
    "topic": "why octopuses have three hearts and blue blood",
    "theme": "science",
    "title": "This Animal Has 3 Hearts and BLUE Blood! #Shorts",
    "description": (
        "Three hearts and blue blood? Meet the octopus. Two hearts pump blood "
        "past its gills; one pumps it around the body. Copper-based hemocyanin "
        "makes oxygenated blood look blue. Sources: Smithsonian Ocean, Natural "
        "History Museum. #Shorts #Octopus #OceanFacts"
    ),
    "tags": ["shorts", "octopus", "three hearts", "blue blood", "marine biology", "animal facts"],
    "scenes": [
        {
            "voiceover": "Three hearts. Blue blood. And eight arms. Meet the octopus.",
            "query": "octopus close up underwater",
            "backup_queries": ["octopus swimming aquarium", "octopus underwater reef"],
            "caption": "Three hearts, blue blood",
        },
        {
            "voiceover": "Two of its hearts move blood past its gills, where it takes up oxygen.",
            "query": "octopus resting underwater",
            "backup_queries": ["octopus undersea reef", "octopus swimming closeup"],
            "caption": "Two hearts serve gills",
        },
        {
            "voiceover": "The third heart pumps oxygen-rich blood through the rest of its body.",
            "query": "octopus crawling seabed",
            "backup_queries": ["octopus walking underwater", "octopus moving reef"],
            "caption": "One serves the body",
        },
        {
            "voiceover": "Human blood uses iron-containing hemoglobin. An octopus uses a copper-containing protein called hemocyanin.",
            "query": "octopus tentacles closeup",
            "backup_queries": ["octopus aquarium arms", "octopus suction cups"],
            "caption": "Copper instead of iron",
        },
        {
            "voiceover": "When that protein carries oxygen, its blood looks blue. Three hearts, one extraordinary animal.",
            "query": "octopus swimming underwater",
            "backup_queries": ["octopus reef closeup", "octopus changing color"],
            "caption": "That is why blood is blue",
        },
    ],
}


def validate() -> None:
    scenes = PLAN["scenes"]
    if len(scenes) != 5 or not 65 <= sum(len(s["voiceover"].split()) for s in scenes) <= 90:
        raise ValueError("Require five engaging, concise scenes and 65-90 spoken words")
    if len(PLAN["title"]) > 65 or "#Shorts" not in PLAN["title"]:
        raise ValueError("Short title incorrect")
    if len({s["query"] for s in scenes}) != len(scenes):
        raise ValueError("Duplicate footage queries")
    for scene in scenes:
        if len(scene["backup_queries"]) != 2:
            raise ValueError("Every beat needs two alternative filmed-footage queries")
        if len(" ".join(scene["voiceover"].split())) < 20:
            raise ValueError("Scene narration too short")
        if any(word.lower() in {"drawing", "diagram", "illustration", "infographic"}
               for word in scene["query"].split()):
            raise ValueError("Slides and cartoons prohibited")
    PLAN["narration"] = " ".join(s["voiceover"] for s in scenes)


def preflight() -> None:
    key = upgrade.bot.PEXELS_API_KEY
    if not key:
        raise RuntimeError("Pexels secret missing; no upload")
    unique: set[int] = set()
    for index, scene in enumerate(PLAN["scenes"], 1):
        available: set[int] = set()
        for query in [scene["query"], *scene["backup_queries"]]:
            response = requests.get(
                "https://api.pexels.com/v1/videos/search",
                headers={"Authorization": key},
                params={"query": query, "orientation": "portrait", "per_page": 15,
                        "page": 1, "locale": "en-US"}, timeout=45,
            )
            response.raise_for_status()
            for item in response.json().get("videos", []):
                if isinstance(item.get("id"), int) and selection_guard._file_options(item):
                    available.add(item["id"])
            if len(available) >= 3:
                break
        print(f"SCENE {index} PORTRAIT STOCK CANDIDATES: {len(available)}", flush=True)
        if not available:
            raise RuntimeError(f"No portrait octopus footage candidate for scene {index}")
        unique.update(available)
    if len(unique) < 5:
        raise RuntimeError("Not enough unique filmed octopus candidates; no upload")
    print(f"PREFLIGHT: {len(unique)} candidate filmed-video IDs across five scenes", flush=True)


def main() -> None:
    validate()
    if (os.getenv("YOUTUBE_PRIVACY") != "public" or
            os.getenv("SHORTS_SKIP_UPLOAD") != "0" or
            os.getenv("GITHUB_RUN_ATTEMPT", "1") != "1"):
        raise RuntimeError("Exactly one explicitly authorized public upload; never rerun one-shot")
    if WORK.exists() or OUT.exists():
        raise RuntimeError("Existing output; duplicate-upload protection")
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
    if (not PLAN.get("visual_review", {}).get("approved") or
            not PLAN.get("live_action_review", {}).get("approved") or
            len({s.get("pexels_video_id") for s in PLAN["scenes"]}) != 5):
        raise RuntimeError("Missing 5 independently approved, distinct filmed scenes; no upload")
    if not state["animated_captions"] or not state["original_music"] or state["motion_clips"] != 5:
        raise RuntimeError("Audio/caption/montage effects not applied; no upload")
    ass = WORK / "captions.ass"
    captions = [line for line in ass.read_text(encoding="utf-8").splitlines() if line.startswith("Dialogue:")]
    if len(captions) < 20:
        raise RuntimeError("Too few timed caption cues; no upload")
    for line in captions:
        caption = line.split(",", 9)[-1]
        import re
        caption = re.sub(r"\{[^}]*\}", "", caption)
        if len(caption) > safe_captions.MAX_CHARS:
            raise RuntimeError("Caption may be cropped on mobile; no upload")
    sources_path = OUT / "visual_sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    for item in sources:
        item["visuals_are_stock_illustrations"] = False
        item["visual_type"] = "filmed_stock_footage"
    sources_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    PLAN["source_reading"] = [
        "https://ocean.si.edu/ocean-life/invertebrates/octopuses-squids-and-relatives",
        "https://www.nhm.ac.uk/discover/octopuses-keep-surprising-us-here-are-eight-examples-how.html",
    ]
    (OUT / "plan.json").write_text(json.dumps(PLAN, ensure_ascii=False, indent=2), encoding="utf-8")
    print("READY VERIFIED SHORT:", PLAN["quality_checks"], "sha256", hashlib.sha256(video.read_bytes()).hexdigest()[:16], flush=True)
    video_id = bot.upload_youtube(video, {key: PLAN[key] for key in ("title", "description", "tags")})
    if not isinstance(video_id, str) or len(video_id) < 6:
        raise RuntimeError("YouTube returned no usable video ID; do not retry automatically")
    print(f"PUBLISHED ONE OCTOPUS SHORT: https://www.youtube.com/shorts/{video_id}", flush=True)


if __name__ == "__main__":
    main()

"""One-shot replacements using real Pexels footage, never diagram posters.

This entrypoint is intentionally NOT a scheduled uploader. Render and review ALL
three distinct Shorts before uploading any. Never rerun after a partial upload.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import montage_fx
import quality_entry as quality
import selection_guard
import upgrade
import visual_guard

bot = upgrade.bot
ROOT = Path(__file__).resolve().parent

# Filmable beats: the same real-life subject remains visible while narration
# explains any invisible science, without pretending microscopic detail is filmed.
PLANS = [
    {
        "slug": "popcorn_real",
        "topic": "why popcorn pops",
        "theme": "everyday",
        "title": "Why Does Popcorn Actually Pop? | Real Footage #Shorts",
        "description": "A real-footage look at how popcorn kernels pop: heat, trapped steam and expanding starch. #Shorts #Popcorn #Science",
        "tags": ["shorts", "popcorn", "food science", "curiosity"],
        "scenes": [
            {"voiceover": "Ever watched a handful of kernels suddenly explode into popcorn? A hot pan brings their hard shells to a temperature where the magic begins.",
             "query": "popcorn popping pan", "backup_queries": ["popcorn cooking pot", "making popcorn stove"], "caption": "Popcorn popping"},
            {"voiceover": "Inside each kernel are water and starch. As it heats, steam becomes trapped, pressure builds, and eventually the shell breaks. Hot starch then expands rapidly.",
             "query": "popcorn popping slow motion", "backup_queries": ["popcorn popping machine", "fresh popcorn popping"], "caption": "Steam builds pressure"},
            {"voiceover": "The expanded starch cools and keeps its fluffy shape. Those crunchy white pieces in your bowl are the result of tiny, edible pressure-cooker experiments.",
             "query": "popcorn bowl closeup", "backup_queries": ["fresh popcorn bowl", "popcorn snack close up"], "caption": "Fluffy popcorn"},
        ],
    },
    {
        "slug": "qrcode_real",
        "topic": "how QR code error correction works",
        "theme": "science",
        "title": "Why Can a Damaged QR Code Still Scan? | Real Video #Shorts",
        "description": "Real footage of QR codes and phone scanning, with a quick explanation of their error correction and its limits. Always check a scanned link. #Shorts #Technology",
        "tags": ["shorts", "qr code", "technology", "error correction"],
        "scenes": [
            {"voiceover": "Have you ever scanned a QR code that looked scratched or faded? Your phone can sometimes read it anyway, thanks to how the code is built.",
             "query": "phone scanning qr code", "backup_queries": ["smartphone qr code scan", "scanning qr code phone"], "caption": "QR codes can survive damage"},
            {"voiceover": "Those big squares in the corners help a camera find and orient the code. Smaller black and white blocks carry information, often a website address.",
             "query": "qr code close up", "backup_queries": ["qr code smartphone", "printed qr code"], "caption": "Patterns help cameras"},
            {"voiceover": "Extra error-correction data can recover some missing blocks, but too much damage still defeats the scanner. And a successful scan never guarantees that a link is safe.",
             "query": "scanning qr code mobile", "backup_queries": ["qr code payment phone", "smartphone scanning qr"], "caption": "Check the destination"},
        ],
    },
    {
        "slug": "flamingo_real",
        "topic": "why flamingos are pink",
        "theme": "science",
        "title": "Why Are Flamingos Pink? | Real Wildlife Footage #Shorts",
        "description": "Real flamingo footage explains how pigments in food contribute to pink and orange feathers. #Shorts #Flamingo #Nature",
        "tags": ["shorts", "flamingo", "wildlife", "nature", "carotenoids"],
        "scenes": [
            {"voiceover": "Flamingos get those bright pink feathers from an unexpected source: their diet. Their striking color is not simply the feather color they start life with.",
             "query": "pink flamingos birds", "backup_queries": ["flamingo wildlife pink", "flamingos standing water"], "caption": "Pink comes from food"},
            {"voiceover": "Wild flamingos eat algae and tiny crustaceans, depending on the species. These foods contain carotenoid pigments, which the birds absorb and process over time.",
             "query": "flamingo feeding water", "backup_queries": ["flamingos eating water", "flamingo feeding lake"], "caption": "Pigments in the diet"},
            {"voiceover": "Those pigments contribute to feathers that can look pink, orange, or reddish. The shade varies with species and diet, so not every flamingo looks equally pink.",
             "query": "flamingos flock pink", "backup_queries": ["flamingo group wildlife", "pink flamingos lake"], "caption": "Different shades of pink"},
        ],
    },
]


def validate() -> None:
    if {p["slug"] for p in PLANS} != {"popcorn_real", "qrcode_real", "flamingo_real"}:
        raise ValueError("Unexpected or duplicate subjects")
    if len({p["title"] for p in PLANS}) != 3:
        raise ValueError("Duplicate video title")
    for plan in PLANS:
        if len(plan["scenes"]) != 3:
            raise ValueError("Exactly three filmable beats per topic required")
        if not 65 <= sum(len(s["voiceover"].split()) for s in plan["scenes"]) <= 105:
            raise ValueError("Narration word count outside expected bounds: " + plan["slug"])
        for scene in plan["scenes"]:
            if len(scene["backup_queries"]) != 2 or not scene["query"]:
                raise ValueError("Each scene requires three stock search options")


def preflight_search() -> None:
    """Cheap API metadata availability check; not a substitute for frame review."""
    import requests
    if not bot.PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY missing; no uploads")
    for plan in PLANS:
        candidate_ids = set()
        for scene in plan["scenes"]:
            count = 0
            for query in (scene["query"], *scene["backup_queries"]):
                response = requests.get(
                    "https://api.pexels.com/v1/videos/search",
                    headers={"Authorization": bot.PEXELS_API_KEY},
                    params={"query": query, "orientation": "portrait", "per_page": 15},
                    timeout=45,
                )
                response.raise_for_status()
                for clip in response.json().get("videos", []):
                    if selection_guard._file_options(clip):
                        count += 1
                        if isinstance(clip.get("id"), int):
                            candidate_ids.add(clip["id"])
                if count >= 3:
                    break
            print(f"PREFLIGHT {plan['slug']}: {scene['query']!r} -> {count} candidate portrait clips", flush=True)
            if count < 1:
                raise RuntimeError(f"No portrait live-action candidates for {plan['slug']}: {scene['query']}")
        if len(candidate_ids) < 3:
            raise RuntimeError(f"Insufficient unique portrait clips for {plan['slug']}")


def main() -> None:
    validate()
    if os.getenv("YOUTUBE_PRIVACY") != "public" or os.getenv("SHORTS_SKIP_UPLOAD") != "0":
        raise RuntimeError("Explicitly authorized public upload required")
    if os.getenv("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise RuntimeError("Never rerun one-shot publishing: prevents duplicate uploads")
    if os.getenv("REAL_SHORTS_PREFLIGHT_ONLY") == "1":
        preflight_search()
        print("PREFLIGHT COMPLETE: no videos rendered or uploaded", flush=True)
        return

    preflight_search()
    # Install the daily bot's animated SINGLE caption layer, subtle camera
    # movement and original low-level audio over actual filmed footage.
    montage_fx.install(quality)
    output_root = ROOT / "real_three_output_20260918"
    work_root = ROOT / "real_three_work_20260918"
    if output_root.exists() or work_root.exists():
        raise RuntimeError("Output already exists; duplicate-run safety guard")
    ready = []
    for plan in PLANS:
        bot.WORK = work_root / plan["slug"]
        bot.OUT = output_root / plan["slug"]
        bot.WORK.mkdir(parents=True, exist_ok=False)
        bot.OUT.mkdir(parents=True, exist_ok=False)
        plan["narration"] = " ".join(scene["voiceover"] for scene in plan["scenes"])
        upgrade.CURRENT_PLAN = plan
        narration = bot.WORK / "voice.wav"
        upgrade.scene_tts(plan["narration"], narration)
        rendered = quality.checked_build(plan, narration)
        if len({s.get("pexels_video_id") for s in plan["scenes"]}) != 3:
            raise RuntimeError("A scene reused footage; no upload")
        if not plan.get("visual_review", {}).get("approved"):
            raise RuntimeError("Scene review did not approve actual rendered footage")
        # Update source manifest: these are recorded live-action assets, not art.
        manifest = bot.OUT / "visual_sources.json"
        info = json.loads(manifest.read_text(encoding="utf-8"))
        for item in info:
            item["visuals_are_stock_illustrations"] = False
            item["visual_type"] = "filmed_stock_footage"
        manifest.write_text(json.dumps(info, indent=2), encoding="utf-8")
        digest = hashlib.sha256(rendered.read_bytes()).hexdigest()
        ready.append((plan, rendered, digest))
        print(f"READY LIVE-ACTION {plan['slug']}: {plan['quality_checks']}", flush=True)
    if len({entry[2] for entry in ready}) != 3:
        raise RuntimeError("Duplicate rendered videos; no upload")
    for plan, rendered, _ in ready:
        video_id = bot.upload_youtube(rendered, {key: plan[key] for key in ("title", "description", "tags")})
        if not video_id:
            raise RuntimeError("YouTube returned no video ID; STOP, never blindly retry")
        print(f"PUBLISHED REAL {plan['slug']}: https://www.youtube.com/shorts/{video_id}", flush=True)
    print("THREE DISTINCT REAL-FOOTAGE PUBLIC SHORTS PUBLISHED", flush=True)


if __name__ == "__main__":
    main()

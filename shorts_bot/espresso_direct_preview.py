"""Reproducible, review-only espresso MP4 from eight previously vision-approved clips.

The source IDs and visible actions were independently verified in Actions run
35478572542. This script retrieves those SAME originals, confirms native-HD
crops, writes an original scene-matched script, speaks it with Kokoro and renders
an MP4 plus review frames. NO YouTube API call exists in this entrypoint.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import requests

import hd_footage_guard
import stock_recovery
import upgrade
import visual_guard

TOPIC = "how an espresso machine brews coffee"
# ID, actual filmed action established by three-frame vision checks in run 35478572542
SHOTS = (
    (28911074, "grinding coffee into the portafilter with an active timer", "espresso grinding coffee"),
    (4374541, "grinding, tamping, and locking the portafilter into the machine", "barista tamping portafilter"),
    (17422066, "espresso liquid pouring from the machine spout into a cup", "espresso extraction pouring"),
    (13737103, "espresso pouring from a portafilter into a white cup", "espresso pouring cup"),
    (6204981, "espresso extracting and dripping into a white cup with visible steam", "espresso extraction steaming"),
    (19709048, "espresso streaming from the portafilter spout into a cup", "espresso stream closeup"),
    (28911071, "espresso extracting and filling a glass cup", "espresso glass cup"),
    (5095328, "espresso flowing into a white cup as its liquid level rises", "espresso cup filling"),
)
WORDS = (
    "Why does finely ground coffee become such a concentrated shot?",
    "The grounds are tamped, then the portafilter locks into place.",
    "Now, hot water flows through the coffee under pressure.",
    "The first dark drops collect in the cup below.",
    "A little steam appears as espresso drips into the cup.",
    "The dark stream keeps flowing through the machine's spout.",
    "Watch the glass fill with a rich, dark espresso shot.",
    "That's espresso: fine grounds, hot water, and pressure. Subscribe for more.",
)
CAPTIONS = (
    "The espresso secret", "Grind, tamp, lock", "Hot water and pressure",
    "The first drops", "Espresso extraction", "A steady stream",
    "A concentrated shot", "Now you know",
)


def _metadata(video_id: int) -> dict:
    response = requests.get(
        f"https://api.pexels.com/videos/videos/{video_id}",
        headers={"Authorization": os.environ["PEXELS_API_KEY"]}, timeout=40,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("id") != video_id:
        raise ValueError(f"Pexels video ID mismatch: {video_id}")
    if not isinstance(result.get("url"), str) or not result["url"].startswith("https://www.pexels.com/video/"):
        raise ValueError("Pexels provenance missing")
    return result


def _download_sources(work: Path) -> tuple[list[Path], list[dict]]:
    sources: list[Path] = []
    evidence: list[dict] = []
    hashes: set[str] = set()
    for number, (video_id, action, query) in enumerate(SHOTS, 1):
        meta = _metadata(video_id)
        options = hd_footage_guard.hd_file_options(meta)
        if not options:
            raise ValueError(f"Approved Pexels {video_id} no longer offers native-HD portrait crop")
        destination = work / f"verified_{number:02d}.mp4"
        errors = []
        for link in options:
            try:
                stock_recovery.download_hd_original(link, destination)
                metadata = json.loads(subprocess.run(
                    ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(destination)],
                    check=True, capture_output=True, text=True,
                ).stdout)
                tracks = [s for s in metadata["streams"] if s.get("codec_type") == "video"]
                if len(tracks) != 1 or int(tracks[0]["width"]) < 1080 or int(tracks[0]["height"]) < 1920:
                    raise ValueError("Source lacks native 1080x1920 crop")
                digest = hashlib.sha256(destination.read_bytes()).hexdigest()
                if digest in hashes:
                    raise ValueError("Duplicate source bytes")
                hashes.add(digest)
                break
            except (requests.RequestException, ValueError, OSError, subprocess.CalledProcessError) as exc:
                destination.unlink(missing_ok=True)
                errors.append(type(exc).__name__)
        if not destination.is_file():
            raise ValueError(f"Unavailable previously approved footage {video_id}: {errors}")
        # Confirm actual 9:16 production crop has three decodable real frames.
        frames = visual_guard.sample_frames(destination, work, f"evidence_{number:02d}")
        if len(frames) != 3:
            raise ValueError("Production crop preview missing")
        sources.append(destination)
        evidence.append({"scene": number, "pexels_video_id": video_id,
                         "pexels_url": meta["url"], "previously_reviewed_action": action,
                         "stock_search": query, "source_sha256": digest,
                         "early_middle_late_cropped_frames": True})
        print(f"ORIGINAL PREVIEW: source {number}/8 restored and cropped: Pexels {video_id}", flush=True)
    return sources, evidence


def main() -> None:
    if os.getenv("SHORTS_SKIP_UPLOAD") != "1":
        raise RuntimeError("This script is preview-only; YouTube upload must stay disabled")
    work = upgrade.bot.WORK
    out = upgrade.bot.OUT
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    sources, evidence = _download_sources(work)
    scenes = []
    for number, ((video_id, action, query), speech, caption) in enumerate(
            zip(SHOTS, WORDS, CAPTIONS), 1):
        scenes.append({"voiceover": speech, "query": query,
                       "backup_queries": ["espresso machine brewing", "coffee barista preparation"],
                       "caption": caption, "pexels_video_id": video_id,
                       "selected_stock_query": query,
                       "preflight_visible_action": action,
                       "stock_source_url": evidence[number - 1]["pexels_url"],
                       "footage_verified_before_script": True})
    plan = {"title": "How Espresso Really Works", "description": (
        "From grinding and tamping to a concentrated espresso shot. "
        "Everyday Mysteries: the little details behind familiar things."),
        "tags": ["espresso", "coffee", "barista", "espresso machine", "coffee brewing"],
        "scenes": scenes, "topic": TOPIC, "theme": "everyday",
        "narration": " ".join(WORDS), "production_order": (
            "Prior three-frame vision approval -> native-HD Pexels source verification -> "
            "original hand-edited factual script -> Kokoro narration -> render -> manual MP4 review"),
        "independent_source_review_run": "35478572542",
        "preview_only": True,
    }
    count = sum(len(upgrade._words(line)) for line in WORDS)
    if not 65 <= count <= 105 or len(set(id for id, _, _ in SHOTS)) != 8:
        raise ValueError("Original script length or stock distinctness failed")
    upgrade.CURRENT_PLAN = plan
    narration = work / "narration.wav"
    upgrade.scene_tts(plan["narration"], narration)
    audio = plan["audio_duration"]
    if not 20 <= audio <= 58:
        raise ValueError("Narration duration invalid")

    def preapproved_scene(scene: dict, index: int) -> Path:
        if plan["scenes"][index] is not scene:
            raise ValueError("Scene provenance mismatch")
        return sources[index]

    upgrade.matched_pexels_video = preapproved_scene
    video = upgrade.aligned_build_video(plan, narration)
    # Save technical evidence and actual final-frame stills for objective review.
    (out / "visual_sources.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    for index, duration in enumerate(plan["scene_durations"]):
        clip = work / f"clip_{index:02d}.mp4"
        stamp = max(0.20, min(float(duration) / 2, float(duration) - .10))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{stamp:.3f}",
                        "-i", str(clip), "-frames:v", "1", "-vf", "scale=405:720",
                        str(out / f"scene_{index + 1:02d}.jpg")],
                       check=True, capture_output=True)
    print(f"ORIGINAL PREVIEW MP4 CREATED: {video}; duration={audio:.2f}s; "
          "YouTube upload DISABLED", flush=True)


if __name__ == "__main__":
    main()

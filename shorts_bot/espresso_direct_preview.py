"""Render a preview-only espresso Short from previously vision-reviewed real clips.

Never silently substitute irrelevant footage, fake sources or publish to YouTube.
Missing stock renditions are logged and skipped, rather than killing the entire
production when six or more independently reviewed suitable originals remain.
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
# Source IDs/actions confirmed from actual cropped three-frame review in run 35478572542.
# Pexels 4374541's HD download was not available in the independent recovery run;
# do not rely on it, repeat other footage or invent another asset.
SHOTS = (
    (28911074, "grinding coffee into the portafilter with an active timer", "espresso grinding coffee",
     "Why does finely ground coffee become such a concentrated shot? Watch the coffee being ground fresh.", "The espresso secret"),
    (17422066, "espresso liquid pouring from the machine spout into a cup", "espresso extraction pouring",
     "Inside the machine, hot water is pushed through finely ground coffee under pressure.", "Water meets coffee"),
    (13737103, "espresso pouring from a portafilter into a white cup", "espresso pouring cup",
     "The first dark drops fall from the portafilter and collect in the cup below.", "The first drops"),
    (6204981, "espresso extracting and dripping into a white cup with visible steam", "espresso extraction steaming",
     "A little steam appears nearby as the espresso continues dripping into the cup.", "Espresso extraction"),
    (19709048, "espresso streaming from the portafilter spout into a cup", "espresso stream closeup",
     "Look closely: the dark stream keeps flowing through the machine's spout.", "A steady stream"),
    (28911071, "espresso extracting and filling a glass cup", "espresso glass cup",
     "The glass gradually fills with a rich, dark, concentrated espresso shot.", "A concentrated shot"),
    (5095328, "espresso flowing into a white cup as its liquid level rises", "espresso cup filling",
     "That's espresso: fine grounds, hot water, and pressure. Follow for more everyday mysteries.", "Now you know"),
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


def _download_sources(work: Path) -> tuple[list[Path], list[dict], list[tuple]]:
    sources: list[Path] = []
    evidence: list[dict] = []
    selected: list[tuple] = []
    hashes: set[str] = set()
    for number, shot in enumerate(SHOTS, 1):
        video_id, action, query, speech, caption = shot
        try:
            meta = _metadata(video_id)
            options = hd_footage_guard.hd_file_options(meta)
            if not options:
                raise ValueError("Pexels metadata no longer offers native HD portrait crop")
            destination = work / f"verified_{number:02d}.mp4"
            errors = []
            digest = None
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
                    visual_guard.sample_frames(destination, work, f"evidence_{number:02d}")
                    hashes.add(digest)
                    break
                except (requests.RequestException, ValueError, OSError, subprocess.CalledProcessError) as exc:
                    destination.unlink(missing_ok=True)
                    errors.append(f"{type(exc).__name__}: {str(exc)[:160]}")
            if not destination.is_file() or digest is None:
                raise ValueError(f"No decodable native HD source: {errors}")
        except (requests.RequestException, ValueError, OSError, subprocess.CalledProcessError) as exc:
            print(f"ORIGINAL PREVIEW: discard unavailable Pexels {video_id}: "
                  f"{type(exc).__name__}: {str(exc)[:220]}", flush=True)
            continue
        sources.append(destination)
        selected.append(shot)
        evidence.append({"scene": len(sources), "pexels_video_id": video_id,
                         "pexels_url": meta["url"], "previously_reviewed_action": action,
                         "stock_search": query, "source_sha256": digest,
                         "early_middle_late_cropped_frames": True})
        print(f"ORIGINAL PREVIEW: approved recovered stock {len(sources)}/{len(SHOTS)}, Pexels {video_id}", flush=True)
    if len(selected) < 6 or SHOTS[0] not in selected:
        raise ValueError(f"Only {len(selected)} usable previously reviewed HD clips; "
                         "need at least 6 including opening preparation")
    return sources, evidence, selected


def main() -> None:
    if os.getenv("SHORTS_SKIP_UPLOAD") != "1":
        raise RuntimeError("Preview-only script: YouTube upload must be disabled")
    work = upgrade.bot.WORK
    out = upgrade.bot.OUT
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    sources, evidence, selected = _download_sources(work)
    scenes = []
    for number, (video_id, action, query, speech, caption) in enumerate(selected, 1):
        scenes.append({"voiceover": speech, "query": query,
                       "backup_queries": ["espresso machine brewing", "coffee barista preparation"],
                       "caption": caption, "pexels_video_id": video_id,
                       "selected_stock_query": query, "preflight_visible_action": action,
                       "stock_source_url": evidence[number - 1]["pexels_url"],
                       "footage_verified_before_script": True})
    narration = " ".join(scene["voiceover"] for scene in scenes)
    total_words = sum(len(upgrade._words(scene["voiceover"])) for scene in scenes)
    if not 65 <= total_words <= 105:
        raise ValueError(f"Narration too short/long: {total_words} words")
    plan = {"title": "How Espresso Really Works", "description": (
        "From grinding to a concentrated espresso shot. "
        "Everyday Mysteries: the little details behind familiar things."),
        "tags": ["espresso", "coffee", "barista", "espresso machine", "coffee brewing"],
        "scenes": scenes, "topic": TOPIC, "theme": "everyday",
        "narration": narration, "production_order": (
            "Prior three-frame vision approval -> native-HD Pexels verification -> "
            "original scene-aligned script -> Kokoro narration -> render -> MP4 review"),
        "independent_source_review_run": "35478572542", "preview_only": True}
    upgrade.CURRENT_PLAN = plan
    voice = work / "narration.wav"
    upgrade.scene_tts(narration, voice)
    if not 20 <= plan["audio_duration"] <= 58:
        raise ValueError("Narration duration outside Shorts range")

    def preapproved_scene(scene: dict, index: int) -> Path:
        if plan["scenes"][index] is not scene:
            raise ValueError("Scene provenance mismatch")
        return sources[index]

    upgrade.matched_pexels_video = preapproved_scene
    video = upgrade.aligned_build_video(plan, voice)
    (out / "visual_sources.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    for index, duration in enumerate(plan["scene_durations"]):
        clip = work / f"clip_{index:02d}.mp4"
        stamp = max(0.20, min(float(duration) / 2, float(duration) - .10))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{stamp:.3f}",
                        "-i", str(clip), "-frames:v", "1", "-vf", "scale=405:720",
                        str(out / f"scene_{index + 1:02d}.jpg")],
                       check=True, capture_output=True)
    print(f"ORIGINAL PREVIEW MP4 CREATED: {video}; duration={plan['audio_duration']:.2f}s; "
          "YouTube upload DISABLED", flush=True)


if __name__ == "__main__":
    main()

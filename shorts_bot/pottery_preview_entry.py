"""Produce a separate pottery-wheel Short for hands-on audiovisual review.

Only licensed Pexels stock is used. This module deliberately has no uploader;
subsequent publication must use the exact reviewed artifact, never rerender it.
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

TOPIC = "how a potter shapes a clay bowl on a wheel"
SEARCHES = (
    "pottery wheel spinning clay", "potter hands shaping clay", "pottery making bowl",
    "pottery wheel close up", "potter smoothing clay", "potter making ceramic bowl",
    "throwing pottery wheel", "clay bowl pottery", "pottery wheel hands",
)
SPEECH = (
    "How does a spinning lump of clay become a bowl?",
    "A potter steadies the wet clay while the wheel keeps turning.",
    "With a little water, careful hands begin changing its shape.",
    "The center opens up, creating space inside the forming bowl.",
    "Small adjustments guide the sides higher as the clay spins.",
    "The potter checks the shape and carefully smooths its edges.",
    "Once shaped, the clay still needs drying and firing before use.",
)
CAPTIONS = (
    "Clay to bowl", "A spinning wheel", "Careful hands", "Shaping the center",
    "Building the walls", "Finishing the rim", "Not finished yet",
)
MIN_SCENES = 7
MAX_CANDIDATES = 65
MAX_DOWNLOADS = 26


def collect() -> list[dict]:
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Pexels credential missing; cannot prove source licensing")
    pool: list[dict] = []
    ids: set[int] = set()
    for query in SEARCHES:
        if len(pool) >= MAX_CANDIDATES:
            break
        for page in (1, 2):
            response = requests.get(
                "https://api.pexels.com/v1/videos/search",
                headers={"Authorization": key},
                params={"query": query, "orientation": "portrait", "per_page": 30,
                        "page": page, "locale": "en-US"}, timeout=40,
            )
            response.raise_for_status()
            added = 0
            for item in response.json().get("videos", []):
                video_id = item.get("id")
                url = item.get("url")
                links = hd_footage_guard.hd_file_options(item)
                if (type(video_id) is not int or video_id <= 0 or video_id in ids
                        or not isinstance(url, str)
                        or not url.startswith("https://www.pexels.com/video/")
                        or not links):
                    continue
                ids.add(video_id)
                pool.append({"id": video_id, "query": query, "url": url, "links": links})
                added += 1
                if added >= 5 or len(pool) >= MAX_CANDIDATES:
                    break
            if added >= 5 or len(pool) >= MAX_CANDIDATES:
                break
    print(f"POTTERY PREVIEW: {len(pool)} distinct native-HD Pexels candidates", flush=True)
    return pool


def recover(pool: list[dict], work: Path) -> list[dict]:
    verified: list[dict] = []
    hashes: set[str] = set()
    for position, item in enumerate(pool[:MAX_DOWNLOADS]):
        target = work / f"pottery_source_{position:02d}.mp4"
        for link in item["links"]:
            try:
                stock_recovery.download_hd_original(link, target)
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(target)],
                    check=True, capture_output=True, text=True,
                )
                tracks = [s for s in json.loads(probe.stdout)["streams"]
                          if s.get("codec_type") == "video"]
                if len(tracks) != 1:
                    raise ValueError("Expected exactly one video track")
                width, height = int(tracks[0]["width"]), int(tracks[0]["height"])
                if min(width, int(height * 9 / 16)) < 1080 or min(height, int(width * 16 / 9)) < 1920:
                    raise ValueError("Native resolution insufficient for 1080x1920 crop")
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                if digest in hashes:
                    raise ValueError("Duplicate source video")
                visual_guard.sample_frames(target, work, f"pottery_evidence_{position:02d}")
                hashes.add(digest)
                verified.append({**item, "path": target, "sha256": digest})
                print(f"POTTERY PREVIEW: recovered unique native-HD clip {len(verified)}/{MIN_SCENES}: {item['id']}", flush=True)
                break
            except (requests.RequestException, OSError, ValueError, subprocess.CalledProcessError) as exc:
                target.unlink(missing_ok=True)
                print(f"POTTERY PREVIEW: rejected {item['id']}: {type(exc).__name__}: {str(exc)[:90]}", flush=True)
        if len(verified) >= MIN_SCENES:
            break
    if len(verified) < MIN_SCENES:
        raise ValueError(f"Only {len(verified)} distinct decodable native-HD clips found; no upload")
    return verified


def main() -> None:
    if os.environ.get("SHORTS_SKIP_UPLOAD") != "1":
        raise RuntimeError("Pottery preview must NEVER publish automatically")
    work, out = upgrade.bot.WORK, upgrade.bot.OUT
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    clips = recover(collect(), work)
    scenes = []
    evidence = []
    for number, (source, speech, caption) in enumerate(zip(clips, SPEECH, CAPTIONS), 1):
        scenes.append({"voiceover": speech, "query": source["query"],
                       "backup_queries": ["potter hands shaping clay", "pottery wheel close up"],
                       "caption": caption, "pexels_video_id": source["id"],
                       "selected_stock_query": source["query"], "stock_source_url": source["url"],
                       "footage_verified_before_script": True})
        evidence.append({"scene": number, "pexels_video_id": source["id"],
                         "pexels_url": source["url"], "sha256": source["sha256"],
                         "early_middle_late_cropped_frames_exported": True})
    plan = {"title": "How Clay Becomes a Bowl", "description": (
                "Watch a potter shape clay on a spinning wheel, from the first touch "
                "to the forming bowl."),
            "tags": ["pottery", "pottery wheel", "clay", "ceramics", "craftsmanship"],
            "topic": TOPIC, "theme": "everyday", "scenes": scenes,
            "narration": " ".join(SPEECH), "preview_only": True,
            "independent_final_vision_review": "Not run; requires direct MP4 audiovisual review before publication"}
    upgrade.CURRENT_PLAN = plan
    voice = work / "narration.wav"
    upgrade.scene_tts(plan["narration"], voice)
    if not 20 <= plan["audio_duration"] <= 58:
        raise ValueError("Invalid narration duration")

    def selected(scene: dict, index: int) -> Path:
        if plan["scenes"][index] is not scene:
            raise ValueError("Scene/source provenance mismatch")
        return clips[index]["path"]

    upgrade.matched_pexels_video = selected
    final = upgrade.aligned_build_video(plan, voice)
    (out / "visual_sources.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    for index, duration in enumerate(plan["scene_durations"]):
        cut = work / f"clip_{index:02d}.mp4"
        for moment, frac in enumerate((.18, .5, .82), 1):
            stamp = max(.10, min(float(duration) * frac, float(duration) - .05))
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{stamp:.3f}",
                            "-i", str(cut), "-frames:v", "1", "-vf", "scale=405:720",
                            str(out / f"scene_{index+1:02d}_{moment}.jpg")],
                           check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"],
                   check=True, capture_output=True)
    (out / "manual_review_required.txt").write_text(
        "MP4 passed decoder and format checks, but final subject/action match and "
        "audible narration MUST be reviewed before publication. No YouTube upload performed.\n",
        encoding="utf-8",
    )
    print(f"POTTERY PREVIEW READY: {final}; duration={plan['audio_duration']:.2f}s; upload OFF", flush=True)


if __name__ == "__main__":
    main()

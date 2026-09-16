"""Fail-closed actual-video review: verify three moments of EVERY selected clip.

An AI vision decision is an imperfect relevance check, not a guarantee of accuracy.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import requests

FRAME_FRACTIONS = (0.18, 0.50, 0.82)


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, text=True, capture_output=True,
    )
    duration = float(result.stdout.strip())
    if not 2.0 <= duration <= 600:
        raise ValueError(f"Stock clip has invalid/short duration: {duration}")
    return duration


def sample_frames(source: Path, work: Path, prefix: str) -> list[bytes]:
    """Use early/mid/late actual footage, not search thumbnail or one lucky frame."""
    duration = _duration(source)
    images: list[bytes] = []
    for number, fraction in enumerate(FRAME_FRACTIONS):
        dest = work / f"{prefix}_{number}.jpg"
        timestamp = min(duration - 0.15, max(0.08, duration * fraction))
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{timestamp:.3f}",
             "-i", str(source), "-frames:v", "1", "-vf", "scale=320:-2",
             "-q:v", "5", str(dest)],
            check=True, capture_output=True,
        )
        image = dest.read_bytes()
        if not 1_000 <= len(image) <= 2_000_000:
            raise ValueError("A clip's preview frame is missing/invalid")
        images.append(image)
    return images


def _model_review(plan: dict[str, Any], previews: list[list[bytes]]) -> list[dict[str, Any]]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("No Gemini key for visual review; publishing blocked")
    if len(plan.get("scenes", [])) != len(previews) or any(len(p) != 3 for p in previews):
        raise ValueError("Every scene needs exactly three actual-frame previews")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()
    parts: list[dict[str, Any]] = [{"text": (
        "You are a strict visual continuity checker, not a fact-checker. "
        "Assess EACH scene separately using ONLY that scene's SPOKEN narration and "
        "its three REAL stock-video frames (EARLY, MIDDLE, LATE). "
        "Do not use subject matter, nouns, examples, or context from other scenes, "
        "other videos, earlier requests, or your own imagined narration. "
        "First identify the exact subject of the quoted scene narration; compare "
        "each frame to that subject and the action actually narrated. "
        "Approve only when the visible subject is exact or a directly relevant, "
        "unmistakable explanatory visual throughout the clip. "
        "Reject footage showing the wrong object, action, location or historical era. "
        "Do not infer invisible objects from narration or stock search terms. "
        "If unsure, reject. Explain your decision with SPECIFIC details visible in "
        "the frames and refer ONLY to the current scene's quoted narration. "
        "NEVER invent or substitute a different narration topic. "
        "Return ONLY JSON: {\"scenes\":[{\"number\":1,\"approved\":false,"
        "\"frames\":[false,false,false],\"evidence\":\"visible subject or mismatch\","
        "\"reason\":\"specific explanation\"}]}. Exactly one result per scene, "
        "frames must contain EXACTLY three booleans; approved=true only if ALL three true."
    )}]
    for number, (scene, images) in enumerate(zip(plan["scenes"], previews), 1):
        parts.append({"text": f"Scene {number} NARRATION: {scene['voiceover']}"})
        for label, image in zip(("EARLY", "MIDDLE", "LATE"), images):
            parts.append({"text": f"Scene {number} {label} frame:"})
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                           "data": base64.b64encode(image).decode("ascii")}})
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"contents": [{"parts": parts}], "generationConfig": {
            "responseMimeType": "application/json", "maxOutputTokens": 4096}},
        timeout=150,
    )
    response.raise_for_status()
    data = response.json()
    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    decisions = json.loads(text).get("scenes")
    if not isinstance(decisions, list) or len(decisions) != len(previews):
        raise ValueError("Vision review returned incomplete decisions")
    return decisions


def verdict(decision: Any, scene_number: int) -> tuple[bool, str]:
    """Malformed, partial and ambiguous AI decisions always mean no approval."""
    if not isinstance(decision, dict) or decision.get("number") != scene_number:
        return False, "missing/misnumbered decision"
    frame_checks = decision.get("frames")
    evidence = decision.get("evidence", "")
    reason = decision.get("reason", "")
    approved = (decision.get("approved") is True and isinstance(frame_checks, list)
                and len(frame_checks) == 3 and all(x is True for x in frame_checks)
                and isinstance(evidence, str) and len(evidence.strip()) >= 12)
    return approved, str(reason if not approved else evidence)[:200]


def review_candidate(scene: dict[str, Any], source: Path, work: Path, index: int) -> tuple[bool, str]:
    """Reject a candidate BEFORE rendering; caller tries the next Pexels clip."""
    frames = sample_frames(source, work, f"candidate_{index:02d}")
    decisions = _model_review({"scenes": [scene]}, [frames])
    return verdict(decisions[0], 1)


def check(plan: dict[str, Any], work: Path, video: Path) -> None:
    """Independent final check. Exception MUST prevent any YouTube upload."""
    if not video.is_file() or not plan.get("scenes"):
        raise ValueError("Missing final video or scene plan")
    scenes = plan["scenes"]
    ids = [s.get("pexels_video_id") for s in scenes]
    if any(type(video_id) is not int or video_id <= 0 for video_id in ids):
        raise ValueError("Missing stock-video provenance; upload cancelled")
    if len(set(ids)) != len(ids):
        raise ValueError("A stock video is repeated between scenes; upload cancelled")
    previews: list[list[bytes]] = []
    for index in range(len(scenes)):
        source = work / f"source_{index:02d}.mp4"
        if not source.is_file():
            raise ValueError(f"Stock clip for scene {index + 1} missing")
        previews.append(sample_frames(source, work, f"final_review_{index:02d}"))
    decisions = _model_review(plan, previews)
    failures = []
    for number, decision in enumerate(decisions, 1):
        approved, explanation = verdict(decision, number)
        if not approved:
            failures.append(f"scene {number}: {explanation}")
    plan["visual_review"] = {"approved": not failures, "scene_decisions": decisions,
                             "frames_checked_per_scene": 3}
    (video.parent / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise ValueError("Final visual mismatch; upload cancelled: " + "; ".join(failures))
    print(f"Final visual review approved {len(scenes)} scenes x 3 frames.", flush=True)

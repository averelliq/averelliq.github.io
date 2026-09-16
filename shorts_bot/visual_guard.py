"""Context-aware, fail-closed visual inspection of the frames viewers will see.

Candidate and final checks inspect matching 9:16 crops and scene-relative moments.
A vision model's judgment is imperfect; uncertainty never authorizes uploading.
"""
from __future__ import annotations

import base64
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import requests

FRAME_FRACTIONS = (0.18, 0.50, 0.82)
CROP_FILTER = (
    "scale=360:640:force_original_aspect_ratio=increase,"
    "crop=360:640,setsar=1,scale=270:480"
)


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, text=True, capture_output=True,
    )
    duration = float(result.stdout.strip())
    if not math.isfinite(duration) or not 2.0 <= duration <= 600:
        raise ValueError(f"Stock clip has invalid/short duration: {duration}")
    return duration


def sample_frames(source: Path, work: Path, prefix: str,
                  displayed_seconds: float | None = None) -> list[bytes]:
    """Preview the production crop and actual displayed early/middle/late times.

    Production loops shorter source footage. Wrapping timestamps mirrors playback.
    """
    duration = _duration(source)
    shown = duration if displayed_seconds is None else float(displayed_seconds)
    if not math.isfinite(shown) or not 2 <= shown <= 60:
        raise ValueError("Invalid scene display duration")
    images: list[bytes] = []
    for number, fraction in enumerate(FRAME_FRACTIONS):
        dest = work / f"{prefix}_{number}.jpg"
        timestamp = min(duration - 0.10, max(0.02, (shown * fraction) % duration))
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{timestamp:.3f}",
             "-i", str(source), "-frames:v", "1", "-vf", CROP_FILTER,
             "-q:v", "4", str(dest)],
            check=True, capture_output=True,
        )
        image = dest.read_bytes()
        if not 1_000 <= len(image) <= 2_000_000:
            raise ValueError("A clip's cropped preview frame is missing/invalid")
        images.append(image)
    return images


def _scene_context(plan: dict[str, Any], index: int) -> dict[str, Any]:
    scenes = plan["scenes"]
    if not 0 <= index < len(scenes):
        raise ValueError("Invalid scene index")
    previous = (scenes[index - 1]["voiceover"] if index else
                plan.get("previous_narration", "(opening scene)"))
    return {"topic": plan.get("topic", ""), "previous_narration": previous,
            "current_narration": scenes[index]["voiceover"]}


def _model_review(plan: dict[str, Any], previews: list[list[bytes]]) -> list[dict[str, Any]]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("No Gemini key for visual review; publishing blocked")
    scenes = plan.get("scenes", [])
    if len(scenes) != len(previews) or any(len(p) != 3 for p in previews):
        raise ValueError("Every scene needs exactly three actual-frame previews")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()
    parts: list[dict[str, Any]] = [{"text": (
        "You are a skeptical visual editor checking STOCK VIDEO, not a fact-checker. "
        "Each scene has an overall TOPIC, its PREVIOUS spoken sentence (ONLY to resolve "
        "pronouns like 'it' and 'this'), and its CURRENT spoken sentence. "
        "Decide ONLY from the CURRENT sentence, using the previous sentence to identify "
        "the actual object. Do not judge by stock search terms or imagined visuals. "
        "The three images are the exact 9:16 CROPPED early, middle and late frames "
        "VIEWERS WILL SEE. Identify the physical object and action in EACH frame. "
        "For a concrete object (e.g. an ice cube in a drink), footage of a related "
        "category (e.g. a sea-ice field, iceberg or ice cave) is NOT the same object. "
        "If the CURRENT sentence refers to 'it', preserve the object's form and setting "
        "from the previous sentence unless it explicitly changes the subject. "
        "Invisible processes (molecular bonds, invisible forces) cannot be witnessed "
        "in ordinary footage: accept ONLY a clear, scientifically appropriate "
        "explanatory animation/diagram OR a plainly relevant view of the SAME physical "
        "object when narration does not imply the invisible process is visible. "
        "An ice cave or pretty crystals DO NOT show hydrogen bonds or a molecular lattice; "
        "abstract decorative lights are not scientific diagrams. "
        "Reject missing required objects, wrong context, irrelevant filler, "
        "unreadable graphics, subject changes, or cropped-out subjects. "
        "When uncertain, reject. Never use another scene's pictures as evidence. "
        "Return ONLY JSON: {\"scenes\":[{\"number\":1,\"approved\":false,"
        "\"frames\":[false,false,false],\"visible_subject\":\"what actually appears\","
        "\"evidence\":\"specific visual proof or mismatch\",\"reason\":\"why\"}]}. "
        "All three frames must individually pass for approved=true. "
        "State what is actually visible, NEVER infer hidden objects or molecules."
    )}]
    for index, (scene, images) in enumerate(zip(scenes, previews)):
        context = _scene_context(plan, index)
        parts.append({"text": (
            f"Scene {index + 1} TOPIC: {context['topic']}; "
            f"PREVIOUS NARRATION: {context['previous_narration']}; "
            f"CURRENT NARRATION: {context['current_narration']}"
        )})
        for label, image in zip(("EARLY", "MIDDLE", "LATE"), images):
            parts.append({"text": f"Scene {index + 1} {label} cropped frame:"})
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
    """Malformed, vague or incomplete answers are never permission to publish."""
    if (not isinstance(decision, dict) or type(decision.get("number")) is not int
            or decision["number"] != scene_number):
        return False, "missing/misnumbered decision"
    checks = decision.get("frames")
    evidence = decision.get("evidence")
    visible = decision.get("visible_subject")
    reason = decision.get("reason")
    approved = (decision.get("approved") is True and isinstance(checks, list)
                and len(checks) == 3 and all(value is True for value in checks)
                and isinstance(visible, str) and len(visible.strip()) >= 5
                and isinstance(evidence, str) and len(evidence.strip()) >= 15
                and isinstance(reason, str) and bool(reason.strip()))
    explanation = f"{visible}: {evidence}" if approved else (reason or evidence or "unclear visual evidence")
    return approved, str(explanation)[:260]


def review_candidate(scene: dict[str, Any], source: Path, work: Path, index: int) -> tuple[bool, str]:
    """Preview actual playback crop and retain prior scene's referent."""
    import upgrade  # Lazy import avoids cycles in isolated tests.

    plan = upgrade.CURRENT_PLAN
    if (not isinstance(plan, dict) or index >= len(plan.get("scenes", []))
            or plan["scenes"][index] is not scene):
        raise ValueError("Cannot prove visual preview belongs to current script")
    length = plan.get("scene_durations", [])[index]
    previews = sample_frames(source, work, f"candidate_{index:02d}", length)
    context = _scene_context(plan, index)
    one_scene = {"topic": context["topic"],
                 "previous_narration": context["previous_narration"],
                 "scenes": [{"voiceover": scene["voiceover"]}]}
    decisions = _model_review(one_scene, [previews])
    return verdict(decisions[0], 1)


def check(plan: dict[str, Any], work: Path, video: Path) -> None:
    """Independently inspect encoded, cropped scene clips; abort before upload."""
    if not video.is_file() or not plan.get("scenes"):
        raise ValueError("Missing final video or scene plan")
    scenes = plan["scenes"]
    ids = [scene.get("pexels_video_id") for scene in scenes]
    if any(type(video_id) is not int or video_id <= 0 for video_id in ids):
        raise ValueError("Missing stock-video provenance; upload cancelled")
    if len(set(ids)) != len(ids):
        raise ValueError("A stock video is repeated between scenes; upload cancelled")
    previews: list[list[bytes]] = []
    for index in range(len(scenes)):
        encoded = work / f"clip_{index:02d}.mp4"
        if not encoded.is_file():
            raise ValueError(f"Rendered scene {index + 1} missing")
        previews.append(sample_frames(encoded, work, f"final_review_{index:02d}"))
    decisions = _model_review(plan, previews)
    failures: list[str] = []
    for number, decision in enumerate(decisions, 1):
        approved, explanation = verdict(decision, number)
        if not approved:
            failures.append(f"scene {number}: {explanation}")
    plan["visual_review"] = {"approved": not failures, "scene_decisions": decisions,
                             "frames_checked_per_scene": 3,
                             "checks_use_rendered_cropped_clips": True}
    (video.parent / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise ValueError("Final visual mismatch; upload cancelled: " + "; ".join(failures))
    print(f"Final rendered-scene review approved {len(scenes)} scenes x 3 frames.", flush=True)

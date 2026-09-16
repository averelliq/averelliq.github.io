"""Fail-closed, scene-by-scene stock-footage relevance check before YouTube upload.

The plan's textual AI review cannot know what a stock search actually returned.
Inspect an extracted frame from every downloaded clip with a vision-capable model.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import requests


def _frame(source: Path, destination: Path) -> bytes:
    duration = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
        capture_output=True, text=True, check=True,
    )
    midpoint = max(0.05, min(float(duration.stdout.strip()) / 2, 3.0))
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{midpoint:.3f}", "-i", str(source),
         "-frames:v", "1", "-vf", "scale=270:-2", "-q:v", "5", str(destination)],
        check=True,
    )
    image = destination.read_bytes()
    if len(image) < 1_000 or len(image) > 2_000_000:
        raise ValueError("Stock preview image is missing or unexpectedly large")
    return image


def _model_review(plan: dict[str, Any], previews: list[bytes]) -> list[dict[str, Any]]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Visual review requires GEMINI_API_KEY; publishing is blocked")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()
    parts: list[dict[str, Any]] = [{"text": (
        "You are a strict video quality reviewer. The following images are actual frames of "
        "the stock clips selected for a YouTube educational Short, one image per numbered scene. "
        "Compare the visible imagery with EACH scene's narration, not the clip's search query. "
        "Approve a scene only if the image depicts the narrated subject or an unmistakably "
        "relevant explanatory visual. REJECT mismatched historical civilizations or eras, "
        "unrelated people, unrelated animals, unrelated household objects, a generic DJ "
        "instead of animal echolocation, irrelevant green screens, unrelated abstract footage, "
        "food already cooked when an unpopped kernel is required, and generic scenery with "
        "no narrated subject. An image of a related category is not enough if the specific "
        "visual meaning is wrong. If uncertain, reject and state why. "
        "Do not try to verify outside facts. Return ONLY JSON with shape "
        '{"scenes":[{"number":1,"approved":false,"reason":"specific visual mismatch"}]}. '
        "Include exactly one decision for each supplied scene."
    )}]
    for i, (scene, image) in enumerate(zip(plan["scenes"], previews), 1):
        parts.append({"text": f"Scene {i}; spoken narration: {scene['voiceover']}"})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image).decode("ascii")}})
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"contents": [{"parts": parts}], "generationConfig": {
            "responseMimeType": "application/json", "maxOutputTokens": 2048}},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    result = json.loads(text)
    decisions = result.get("scenes")
    if not isinstance(decisions, list) or len(decisions) != len(previews):
        raise ValueError("Visual review returned an incomplete scene count")
    return decisions


def check(plan: dict[str, Any], work: Path, video: Path) -> None:
    """Raise on any uncertainty; the caller must NEVER upload after failure."""
    if not video.is_file() or not plan.get("scenes"):
        raise ValueError("Missing video or approved scene plan")
    scenes = plan["scenes"]
    ids = [s.get("pexels_video_id") for s in scenes]
    if any(not isinstance(video_id, int) or video_id <= 0 for video_id in ids):
        raise ValueError("Stock footage provenance missing; upload cancelled")
    if len(set(ids)) != len(ids):
        raise ValueError("The same stock video was used in multiple scenes; upload cancelled")
    previews = []
    for index in range(len(scenes)):
        source = work / f"source_{index:02d}.mp4"
        if not source.is_file():
            raise ValueError(f"Scene {index + 1} has no downloaded stock footage")
        previews.append(_frame(source, work / f"review_{index:02d}.jpg"))
    decisions = _model_review(plan, previews)
    failures = []
    for number, decision in enumerate(decisions, 1):
        if (not isinstance(decision, dict) or decision.get("number") != number
                or decision.get("approved") is not True):
            reason = decision.get("reason", "missing approval") if isinstance(decision, dict) else "invalid response"
            failures.append(f"scene {number}: {str(reason)[:140]}")
    plan["visual_review"] = {"approved": not failures, "scene_decisions": decisions}
    (video.parent / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise ValueError("Visual footage mismatch; upload cancelled: " + "; ".join(failures))
    print(f"Visual review approved all {len(scenes)} actual stock-footage scenes.", flush=True)

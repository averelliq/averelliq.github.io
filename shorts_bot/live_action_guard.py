"""Fail-closed photographic video gate for scheduled and one-shot Shorts.

Keep searching when footage is illustrated; an unavailable model blocks upload.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import requests
import visual_guard


class NotLiveFootage(ValueError):
    """A functioning model found an illustration, slide or inconclusive frame."""


_PROMPT = (
    "You are an exacting video QC reviewer. These are three frames extracted "
    "from ONE clip that will appear in a YouTube Short. The user's requirement "
    "is ACTUAL REAL-WORLD CAMERA FOOTAGE, not a slideshow. For EACH frame decide "
    "whether the image visibly depicts a genuine real-life subject FILMED BY A "
    "CAMERA. Reject vector art, illustrations, diagrams, icons, infographic "
    "slides, rendered 3D/CGI, AI-drawn images, screenshots/screen recordings, "
    "plain backgrounds, fake-looking poster compositions or frames dominated "
    "by large pre-existing headings/subtitles. A QR code physically printed "
    "on a real sign or a real phone scanning a QR code IS valid filmed footage; "
    "an isolated digitally drawn QR pattern filling a slide is NOT. "
    "Photographs digitally zoomed into a static screen are not moving live "
    "footage. If unsure, reject. Respond with ONLY strict JSON: "
    '{"filmed":true,"frames":[true,true,true],"subject":"specific observed real subject",'
    '"reason":"specific evidence supporting all frame decisions"}. '
    "filmed=true ONLY if ALL THREE frames show appropriate real-world "
    "camera footage, with no illustrative or text-slide substitutions."
)


def _verify(images: list[bytes], label: str) -> str:
    if len(images) != 3 or any(len(image) < 1000 for image in images):
        raise ValueError(f"{label}: incomplete photographic frames; publishing blocked")
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError("No Gemini API key for real-footage verification; publishing blocked")
    parts = [{"text": _PROMPT + " Frame order: early, middle, late."}]
    for name, image in zip(("EARLY", "MIDDLE", "LATE"), images):
        parts.append({"text": name + " frame:"})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image).decode("ascii")}})
    failures = []
    for model in ("gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"):
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json={"contents": [{"parts": parts}], "generationConfig": {
                    "responseMimeType": "application/json", "temperature": 0,
                    "maxOutputTokens": 1536}}, timeout=120,
            )
            response.raise_for_status()
            result = response.json()
            text = "".join(part.get("text", "") for part in result["candidates"][0]["content"]["parts"])
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")
            checks = data.get("frames")
            if (data.get("filmed") is not True or not isinstance(checks, list)
                    or len(checks) != 3 or any(flag is not True for flag in checks)):
                raise NotLiveFootage(f"{label}: not reliably filmed real-world footage: {str(data.get('reason'))[:240]}")
            subject = data.get("subject")
            reason = data.get("reason")
            if not isinstance(subject, str) or len(subject.strip()) < 5 or not isinstance(reason, str) or len(reason.strip()) < 12:
                raise NotLiveFootage(f"{label}: photographic proof missing")
            print(f"FILMED FOOTAGE APPROVED {label}: {subject[:90]} — {reason[:140]}", flush=True)
            return subject[:200]
        except (requests.RequestException, KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
            if isinstance(exc, NotLiveFootage):
                raise
            failures.append(f"{model}: {type(exc).__name__}")
            continue
    raise RuntimeError(f"{label}: cannot verify live-action video; upload cancelled: {'; '.join(failures)}")


def install() -> None:
    if getattr(visual_guard, "_live_action_installed", False):
        return
    previous_candidate = visual_guard.review_candidate
    previous_final = visual_guard.check

    def filmed_candidate(scene, source: Path, work: Path, index: int):
        approved, explanation = previous_candidate(scene, source, work, index)
        if not approved:
            return approved, explanation
        files = [work / f"candidate_{index:02d}_{number}.jpg" for number in range(3)]
        try:
            proof = _verify([path.read_bytes() for path in files], f"candidate scene {index + 1}")
        except NotLiveFootage as exc:
            return False, str(exc)
        scene["live_action_evidence"] = proof
        return True, explanation + "; filmed: " + proof

    def filmed_final(plan, work: Path, video: Path):
        previous_final(plan, work, video)
        proofs = []
        for index in range(len(plan["scenes"])):
            files = [work / f"final_review_{index:02d}_{number}.jpg" for number in range(3)]
            proofs.append(_verify([path.read_bytes() for path in files], f"rendered scene {index + 1}"))
        plan["live_action_review"] = {"approved": True, "all_scenes_filmed": True, "evidence": proofs}
        (video.parent / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"LIVE-ACTION FINAL QC PASSED: {len(proofs)} real filmed scenes", flush=True)

    visual_guard.review_candidate = filmed_candidate
    visual_guard.check = filmed_final
    visual_guard._live_action_installed = True

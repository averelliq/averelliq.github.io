"""Resilient, conservative early/middle/late footage review.

Gemini can return JSON arrays despite an object-shaped response request, or truncate
large responses. Review in small batches, normalize only an unambiguous array shape,
retry malformed replies individually, and never treat invalid/missing fields as approval.
"""
from __future__ import annotations

import base64
import json

import footage_first

_installed = False


def _review(topic, items):
    key = footage_first.os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Cannot review footage without Gemini API access")
    parts = [{"text": (
        "Check this camera-shot inventory BEFORE any YouTube Short is scripted. "
        f"The intended subject is: {topic}. Each numbered clip has three actual "
        "9:16-cropped frames, early/middle/late. For EACH clip reject wrong subjects, "
        "unrelated scenery, static slides, AI/CGI pictures, pre-existing overlaid "
        "text, uncertain footage or a cropped-out subject. Require real-world "
        "filmed action OR visibly changing camera perspective across the three "
        "frames; do NOT infer motion from one still. A shot may show an observable "
        "object rather than invisible mechanics, but MUST belong to this subject. "
        "Return strict JSON "
        '{"clips":[{"number":1,"approved":true,"frames":[true,true,true],'
        '"filmed":true,"motion_visible":true,"visible_subject":"specific physical thing",'
        '"visible_action":"specific observed movement or viewpoint change",'
        '"evidence":"specific observations across all frames"}]}. '
        "Every field is mandatory; be conservative."
    )}]
    for index, item in enumerate(items, 1):
        parts.append({"text": f"CLIP {index}: early, middle, late, respectively."})
        for image in item["previews"]:
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                           "data": base64.b64encode(image).decode("ascii")}})
    response = footage_first.requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{footage_first.upgrade.bot.GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": parts}], "generationConfig": {
            "responseMimeType": "application/json", "temperature": 0,
            "maxOutputTokens": 4096}}, timeout=150,
    )
    response.raise_for_status()
    text = "".join(p.get("text", "") for p in response.json()["candidates"][0]["content"]["parts"])
    payload = json.loads(text)
    # Some valid model responses are a bare array despite the requested envelope.
    if isinstance(payload, dict) and set(payload) == {"clips"}:
        results = payload["clips"]
    elif isinstance(payload, list):
        results = payload
    else:
        raise ValueError("Unexpected preliminary review JSON shape; no approval")
    if not isinstance(results, list) or len(results) != len(items):
        raise ValueError("Incomplete preliminary footage review; no approval")
    decisions = []
    for number, (item, result) in enumerate(zip(items, results), 1):
        if not isinstance(result, dict) or type(result.get("number")) is not int or result["number"] != number:
            raise ValueError("Misnumbered footage review; no approval")
        approved = (result.get("approved") is True and result.get("filmed") is True
                    and result.get("motion_visible") is True
                    and result.get("frames") == [True, True, True]
                    and all(isinstance(result.get(k), str) and len(result[k].strip()) >= 12
                            for k in ("visible_subject", "visible_action", "evidence")))
        decisions.append(approved)
        if approved:
            item["observed_subject"] = result["visible_subject"].strip()[:180]
            item["observed_action"] = result["visible_action"].strip()[:180]
            item["preflight_evidence"] = result["evidence"].strip()[:300]
        else:
            print(f"FOOTAGE FIRST: clip {item['id']} fails topic/action review", flush=True)
    return decisions


def install() -> None:
    global _installed
    if _installed:
        return

    def review_in_small_batches(topic, items):
        decisions = []
        for start in range(0, len(items), 2):
            batch = items[start:start + 2]
            try:
                decisions.extend(_review(topic, batch))
                continue
            except (json.JSONDecodeError, ValueError, KeyError, IndexError,
                    TypeError, AttributeError) as exc:
                print(f"FOOTAGE REVIEW: invalid batch {start + 1}-{start + len(batch)} "
                      f"({type(exc).__name__}); retry each clip", flush=True)
            for item in batch:
                accepted = False
                for attempt in range(2):
                    try:
                        verdict = _review(topic, [item])
                        accepted = len(verdict) == 1 and verdict[0] is True
                        break
                    except (json.JSONDecodeError, ValueError, KeyError, IndexError,
                            TypeError, AttributeError) as exc:
                        print(f"FOOTAGE REVIEW: clip {item['id']} response invalid "
                              f"({type(exc).__name__}, attempt {attempt + 1}/2); "
                              "never assume approval", flush=True)
                decisions.append(accepted)
        if len(decisions) != len(items):
            raise ValueError("Footage review count inconsistent; no upload")
        return decisions

    footage_first._vision = review_in_small_batches
    _installed = True

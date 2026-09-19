"""Footage-first Shorts: verify usable Pexels HD camera footage BEFORE writing.

Third-party YouTube videos supply topic inspiration only, never unlicensed assets.
Existing scene-specific and final quality checks remain mandatory.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import requests

import creator_guard
import hd_footage_guard
import quality_entry
import selection_guard
import stock_recovery
import trend_ideas
import upgrade
import visual_guard

BANK = {
    "science": (
        ("how a magnet attracts metal", ("magnet attracting metal", "magnet picking up nails", "magnet metal objects")),
        ("how a spinning top stays upright", ("spinning top closeup", "wooden spinning top", "spinning toy top")),
        ("how a hummingbird hovers", ("hummingbird hovering closeup", "hummingbird feeding flowers", "hummingbird flying slow motion")),
        ("how a prism splits light", ("glass prism rainbow", "prism sunlight rainbow", "light through prism")),
    ),
    "history": (
        ("how a traditional pottery wheel works", ("pottery wheel spinning", "potter making pottery", "clay pottery wheel")),
        ("how a blacksmith shapes iron", ("blacksmith forging iron", "blacksmith hammering metal", "traditional blacksmith workshop")),
        ("how a traditional printing press works", ("printing press working", "letterpress printing machine", "old printing press")),
        ("how a mechanical clock works", ("mechanical clock gears", "antique clock mechanism", "clock gears turning")),
    ),
    "everyday": (
        ("how an espresso machine brews coffee", ("espresso machine brewing", "espresso coffee pouring", "barista making espresso")),
        ("how a zipper closes", ("zipper closing closeup", "zipper being zipped", "zipper close up")),
        ("how a bicycle gear changes", ("bicycle gears moving", "bike chain gears", "bicycle gear shifting")),
        ("why a candle flame flickers", ("candle flame flickering", "burning candle closeup", "single candle flame")),
    ),
}
SPECIAL = {
    "why airplane windows are rounded": (
        "airplane oval window", "airplane cabin windows", "airplane window closeup",
        "passenger airplane window", "airplane interior windows",
    ),
}
MIN_SHOTS = 8
MAX_DOWNLOADS_PER_TOPIC = 12
_inventory: list[dict[str, Any]] = []
_plan: dict[str, Any] | None = None
_installed = False


def _search(topic: str, queries: tuple[str, ...]) -> list[dict[str, Any]]:
    if not upgrade.bot.PEXELS_API_KEY:
        raise RuntimeError("Pexels API key missing; cannot establish footage source")
    pool: list[dict[str, Any]] = []
    seen: set[int] = set()
    for query in queries:
        if len(pool) >= MAX_DOWNLOADS_PER_TOPIC + 3:
            break
        per_query = 0
        for page in (1, 2):
            response = requests.get(
                "https://api.pexels.com/v1/videos/search",
                headers={"Authorization": upgrade.bot.PEXELS_API_KEY},
                params={"query": query, "orientation": "portrait", "per_page": 30,
                        "page": page, "locale": "en-US"}, timeout=40,
            )
            response.raise_for_status()
            for video in response.json().get("videos", []):
                identifier = video.get("id")
                if type(identifier) is not int or identifier <= 0 or identifier in seen:
                    continue
                options = hd_footage_guard.hd_file_options(video)
                url = video.get("url")
                if not options or not isinstance(url, str) or not url.startswith("https://www.pexels.com/video/"):
                    continue
                seen.add(identifier)
                pool.append({"id": identifier, "url": url, "query": query,
                             "file_urls": options})
                per_query += 1
                if per_query >= 6:
                    break
            if per_query >= 6 or len(pool) >= MAX_DOWNLOADS_PER_TOPIC + 3:
                break
    print(f"FOOTAGE FIRST: {topic!r}: {len(pool)} distinct Pexels Full HD assets found", flush=True)
    return pool


def _download(candidate: dict[str, Any], position: int) -> dict[str, Any] | None:
    dest = upgrade.bot.WORK / f"preflight_{position:02d}.mp4"
    dest.unlink(missing_ok=True)
    for link in candidate["file_urls"]:
        try:
            stock_recovery.download_hd_original(link, dest)
            fingerprint = selection_guard._fingerprint(dest)
            frames = visual_guard.sample_frames(dest, upgrade.bot.WORK, f"preflight_{position:02d}")
            return {**candidate, "path": dest, "fingerprint": fingerprint,
                    "previews": frames}
        except (requests.RequestException, OSError, ValueError, RuntimeError,
                subprocess.CalledProcessError) as exc:
            dest.unlink(missing_ok=True)
            print(f"FOOTAGE FIRST: reject damaged HD source {candidate['id']} ({type(exc).__name__})", flush=True)
    return None


def _vision(topic: str, items: list[dict[str, Any]]) -> list[bool]:
    """Inspect actual cropped early/middle/late frames before script creation."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Cannot review footage without Gemini API access")
    parts: list[dict[str, Any]] = [{"text": (
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
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{upgrade.bot.GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": parts}], "generationConfig": {
            "responseMimeType": "application/json", "temperature": 0,
            "maxOutputTokens": 4096}}, timeout=150,
    )
    response.raise_for_status()
    text = "".join(p.get("text", "") for p in response.json()["candidates"][0]["content"]["parts"])
    results = json.loads(text).get("clips")
    if not isinstance(results, list) or len(results) != len(items):
        raise ValueError("Incomplete preliminary footage review; upload cancelled")
    decisions: list[bool] = []
    for number, (item, result) in enumerate(zip(items, results), 1):
        if not isinstance(result, dict) or type(result.get("number")) is not int or result["number"] != number:
            raise ValueError("Misnumbered footage review; upload cancelled")
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


def _prepare(topic: str, queries: tuple[str, ...]) -> list[dict[str, Any]] | None:
    pool = _search(topic, queries)
    if len(pool) < MIN_SHOTS:
        return None
    downloaded: list[dict[str, Any]] = []
    fingerprints: list[int] = []
    for position, candidate in enumerate(pool[:MAX_DOWNLOADS_PER_TOPIC]):
        clip = _download(candidate, position)
        if clip is None:
            continue
        if any((clip["fingerprint"] ^ prior).bit_count() <= 4 for prior in fingerprints):
            clip["path"].unlink(missing_ok=True)
            continue
        fingerprints.append(clip["fingerprint"])
        downloaded.append(clip)
        if len(downloaded) >= MIN_SHOTS + 2:
            break
    if len(downloaded) < MIN_SHOTS:
        return None
    approved: list[dict[str, Any]] = []
    verdicts = _vision(topic, downloaded)
    for clip, verdict in zip(downloaded, verdicts):
        if verdict:
            approved.append(clip)
        else:
            clip["path"].unlink(missing_ok=True)
    if len(approved) < MIN_SHOTS:
        return None
    for extra in approved[MIN_SHOTS:]:
        extra["path"].unlink(missing_ok=True)
    return approved[:MIN_SHOTS]


def _seed(theme: str) -> str:
    previous = trend_ideas._CACHE.get(theme)
    if previous:
        return previous
    return trend_ideas.pick_topic(theme, quality_entry._original_choose_topic,
                                  quality_entry._original_model_json)


def _candidates(theme: str, seed: str):
    if os.getenv("SHORTS_ONE_OFF_PUBLISH") == "1":
        queries = SPECIAL.get(seed)
        if not queries:
            raise ValueError("One-off topic lacks footage-first queries; no topic substitution")
        return [(seed, queries)]
    seed_queries = SPECIAL.get(seed)
    if seed_queries is None:
        words = re.findall(r"[a-z]+", seed.lower())
        words = [w for w in words if w not in {"why", "how", "the", "a", "an", "are", "is"}]
        seed_queries = (" ".join(words[:5]),) if 2 <= len(words) <= 9 else ()
    result = [(seed, seed_queries)] if seed_queries else []
    return result + [(topic, queries) for topic, queries in BANK[theme] if topic != seed]


def _check_audio(plan: dict[str, Any], destination: Path) -> None:
    import numpy as np
    import soundfile as sf

    data, rate = sf.read(destination, dtype="float32")
    if rate != 24000 or data.ndim != 1 or len(data) < rate * 20:
        raise ValueError("Narration format/length invalid; upload cancelled")
    if not np.isfinite(data).all() or np.max(np.abs(data)) > .998:
        raise ValueError("Narration has invalid samples/clipping; upload cancelled")
    if float(np.sqrt(np.mean(data * data))) < .009:
        raise ValueError("Narration almost silent; upload cancelled")
    for index, seconds in enumerate(plan["scene_durations"]):
        if not 1.0 < float(seconds) < 12.0:
            raise ValueError(f"Scene {index + 1} voice duration invalid")
    plan["voice_qc"] = "24 kHz mono; finite samples, peak, level and scene durations checked"


def install() -> None:
    global _installed
    if _installed:
        return
    original_generate = quality_entry.upgrade.generate_plan
    original_model = quality_entry._original_model_json
    original_voice = upgrade.scene_tts

    def inventory_model(prompt: str):
        if prompt.startswith("You are an English-language, original educational Shorts scriptwriter"):
            if len(_inventory) != MIN_SHOTS:
                raise RuntimeError("No approved real footage available BEFORE script")
            shots = [{"scene": i + 1, "search_query": item["query"],
                      "actually_visible": item["observed_subject"],
                      "actual_action": item["observed_action"]}
                     for i, item in enumerate(_inventory)]
            prompt += ("\nFOOTAGE-FIRST MANDATE: The following eight distinct, Pexels-sourced, "
                       "portrait Full HD REAL VIDEO clips were downloaded and visually "
                       "approved BEFORE this script. Script scene N must truthfully "
                       "describe ONLY what its corresponding clip N can show. "
                       "Use the exact search_query for each numbered scene; no "
                       "extra objects, imaginary shots, fake demonstrations, "
                       "claims that invisible physics is visible, or invented facts. "
                       "Open by describing an actual visible action in clip 1. "
                       "Keep English natural and total spoken length near 25-30 seconds. "
                       "The final scene answers the hook before any CTA. "
                       "This inventory is visual evidence, NOT external fact checking: "
                       + json.dumps(shots, ensure_ascii=False))
        return original_model(prompt)

    def generate_from_footage():
        global _inventory, _plan
        _inventory = []
        _plan = None
        theme = upgrade.select_theme()
        seed = _seed(theme)
        history, _, _, _ = creator_guard._history()
        prior_topics = {str(item.get("topic", "")) for item in history}
        for topic, queries in _candidates(theme, seed):
            if creator_guard._slug(topic) in prior_topics:
                print(f"FOOTAGE FIRST: skip previously published/reserved topic: {topic}", flush=True)
                continue
            if not queries:
                continue
            print(f"FOOTAGE FIRST: checking available clips BEFORE writing: {topic}", flush=True)
            inventory = _prepare(topic, tuple(queries))
            if inventory is not None:
                _inventory = inventory
                trend_ideas._CACHE[theme] = topic
                if topic != seed:
                    trend_ideas._REFERENCES.pop(theme, None)
                print(f"FOOTAGE FIRST: {MIN_SHOTS} different real Full HD clips approved for {topic}", flush=True)
                break
            print(f"FOOTAGE FIRST: no complete approved eight-shot set for {topic}", flush=True)
        if len(_inventory) != MIN_SHOTS:
            upgrade.bot.die("No topic has eight suitable Pexels Full HD filmed shots; no script or upload")
        plan = original_generate()
        if plan.get("topic") != trend_ideas._CACHE[theme] or len(plan.get("scenes", [])) != MIN_SHOTS:
            raise ValueError("Script changed the approved footage topic/scene count; upload cancelled")
        for scene, clip in zip(plan["scenes"], _inventory):
            scene["query"] = clip["query"]
            # Keep already-reviewed natural backup phrases as metadata; the picker
            # below may ONLY select the pre-approved asset.
            scene["preflight_visible_subject"] = clip["observed_subject"]
            scene["preflight_visible_action"] = clip["observed_action"]
            scene["stock_source_url"] = clip["url"]
            scene["footage_verified_before_script"] = True
        plan["production_order"] = "Pexels discovery -> HD camera review -> original script -> scene review -> render -> final QC"
        plan["footage_rights_basis"] = "Pexels video source; check Pexels license and third-party rights restrictions"
        _plan = plan
        return plan

    def preapproved_pick(scene: dict[str, Any], index: int) -> Path:
        if (_plan is None or upgrade.CURRENT_PLAN is not _plan or not 0 <= index < MIN_SHOTS
                or _plan["scenes"][index] is not scene):
            raise ValueError("Pre-approved footage does not match current approved script")
        clip = _inventory[index]
        path = clip["path"]
        if not path.is_file() or visual_guard._duration(path) < 2:
            raise ValueError("Pre-approved source missing/corrupt; no irrelevant fallback footage")
        approved, proof = visual_guard.review_candidate(scene, path, upgrade.bot.WORK, index)
        if not approved:
            raise ValueError(f"Scene {index + 1} does not match its preselected footage: {proof}")
        dest = upgrade.bot.WORK / f"source_{index:02d}.mp4"
        shutil.copyfile(path, dest)
        scene["pexels_video_id"] = clip["id"]
        scene["selected_stock_query"] = clip["query"]
        scene["preview_review"] = {"approved": True, "three_frames_checked": True,
                                   "visible_evidence": proof}
        return dest

    def verified_voice(text: str, destination: Path) -> None:
        original_voice(text, destination)
        if upgrade.CURRENT_PLAN is None:
            raise ValueError("Approved script missing for voice QA")
        _check_audio(upgrade.CURRENT_PLAN, destination)

    quality_entry._original_model_json = inventory_model
    quality_entry.upgrade.generate_plan = generate_from_footage
    upgrade.matched_pexels_video = preapproved_pick
    upgrade.scene_tts = verified_voice
    _installed = True

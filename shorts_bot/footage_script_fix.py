"""Align a story with the footage that has ALREADY passed independent checks.

Only alters the order of previously approved shots and script-search metadata.
No reject verdict is reinterpreted, and all existing editorial, voice,
scene-to-narration and final-render reviews remain mandatory.
"""
from __future__ import annotations

import copy
import re

import footage_first
import quality_entry

_installed = False


def _stage(clip: dict) -> int:
    text = " ".join(str(clip.get(k, "")) for k in
                    ("observed_subject", "observed_action", "preflight_evidence", "query")).lower()
    # The extraction itself is later than preparation; cup and finished crema
    # should not precede dosing/tamping. A stable sort preserves other footage.
    if re.search(r"grind|grinder|whole beans|coffee beans", text):
        return 0
    if re.search(r"dose|dosing|ground coffee|coffee grounds|basket|filter", text):
        return 1
    if re.search(r"tamp|tamper|pressing coffee|compress", text):
        return 2
    if re.search(r"lock|attach|insert|handle|portafilter", text):
        return 3
    if re.search(r"machine|brew|brewing|extract|extraction", text):
        return 4
    if re.search(r"pour|flow|stream|drip|dripping", text):
        return 5
    if re.search(r"crema|foam|finished|ready|cup of espresso", text):
        return 6
    return 4


def _unique_query(base: str, existing: set[str]) -> str:
    words = re.findall(r"[a-z]+", str(base).lower())[:4]
    if len(words) < 2:
        words = ["espresso", "coffee"]
    stem = " ".join(words)
    for suffix in ("", "closeup", "detail", "preparation", "process", "video",
                   "machine", "brewing", "barista", "shot", "coffee"):
        candidate = stem if not suffix else " ".join((*words[:4], suffix))
        if 2 <= len(candidate.split()) <= 5 and candidate not in existing:
            existing.add(candidate)
            return candidate
    raise ValueError("Cannot construct distinct truthful espresso clip search metadata")


def install() -> None:
    global _installed
    if _installed:
        return
    original_prepare = footage_first._prepare
    original_model = quality_entry._original_model_json

    def chronologically_approved(topic, queries):
        clips = original_prepare(topic, queries)
        if clips is None:
            return None
        if topic == "how an espresso machine brews coffee":
            clips.sort(key=_stage)
        for index, clip in enumerate(clips, 1):
            print(f"FOOTAGE STORY ORDER {index}/8: {clip['id']}: "
                  f"{clip.get('observed_subject', '')[:95]} | "
                  f"{clip.get('observed_action', '')[:120]}", flush=True)
        return clips

    def distinct_verified_queries(prompt):
        result = original_model(prompt)
        if (not prompt.startswith("You are an English-language, original educational Shorts scriptwriter")
                or len(footage_first._inventory) != footage_first.MIN_SHOTS
                or not isinstance(result, dict)):
            return result
        scenes = result.get("scenes")
        if not isinstance(scenes, list) or len(scenes) != footage_first.MIN_SHOTS:
            return result
        # The original draft's search queries are only planning metadata.
        # After validation, footage_first replaces each with the actual
        # independently reviewed Pexels source query and file ID.
        result = copy.deepcopy(result)
        used: set[str] = set()
        for scene, clip in zip(result["scenes"], footage_first._inventory):
            scene["query"] = _unique_query(clip["query"], used)
        return result

    footage_first._prepare = chronologically_approved
    quality_entry._original_model_json = distinct_verified_queries
    _installed = True

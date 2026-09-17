"""Generate the serious long-form KAYIP FREKANS_ test story with Ollama.

The story itself starts with a concrete hook. The short channel intro is inserted
AFTER the hook so the first seconds are not spent on a generic greeting.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import bot
import cloud_v3
import mpt_profile


def compose(topic: str, minutes: int, output: Path) -> dict:
    if not 15 <= minutes <= 20:
        raise ValueError("Serious long test target must be 15-20 minutes")
    output.mkdir(parents=True, exist_ok=True)

    title, parts, report = cloud_v3.create_story(topic, minutes, preview=False)
    if len(parts) < 2:
        raise ValueError("Long story did not contain story chapters")

    intro = parts[0].strip()
    chapters = [p.strip() for p in parts[1:] if p.strip()]
    story_only = "\n\n".join(chapters)
    story_check = mpt_profile.check_story(story_only, minutes, preview=False)

    first_sentences = bot.sentences(chapters[0])
    if len(first_sentences) < 3:
        raise ValueError("Opening chapter is too short for a hook-first intro")
    hook = []
    hook_words = 0
    split_at = 0
    for index, sentence in enumerate(first_sentences):
        hook.append(sentence)
        hook_words += len(sentence.split())
        split_at = index + 1
        if hook_words >= 38 and index >= 1:
            break
    if hook_words < 25:
        raise ValueError("Opening hook is too short")

    opening_rest = " ".join(first_sentences[split_at:]).strip()
    narration_parts = [" ".join(hook), intro]
    if opening_rest:
        narration_parts.append(opening_rest)
    narration_parts.extend(chapters[1:])
    narration = "\n\n".join(narration_parts).strip()

    if narration.casefold().startswith("merhaba"):
        raise ValueError("Channel intro was incorrectly placed before the hook")
    if "Kayıp Frekans" not in intro:
        raise ValueError("Channel intro is missing")

    (output / "story.txt").write_text(story_only + "\n", encoding="utf-8")
    (output / "narration_script.txt").write_text(narration + "\n", encoding="utf-8")
    state = {
        "title": title,
        "topic": topic,
        "target_minutes": minutes,
        "story_words": len(story_only.split()),
        "narration_words": len(narration.split()),
        "hook_words": hook_words,
        "intro": intro,
        "story_check": story_check,
        "editor_report": report,
        "hook_first": True,
        "channel_intro_after_hook": True,
        "youtube_uploaded": False,
    }
    (output / "story_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "title": title,
        "story_words": state["story_words"],
        "narration_words": state["narration_words"],
        "hook_words": hook_words,
        "hook_first": True,
    }, ensure_ascii=False), flush=True)
    return state


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--output", type=Path, default=Path("output/long-test"))
    args = p.parse_args()
    compose(args.topic, args.minutes, args.output)

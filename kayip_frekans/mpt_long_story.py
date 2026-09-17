"""Generate a serious long-form KAYIP FREKANS_ story with Ollama.

The story starts with a concrete hook and places the short channel intro after
that hook. Story generation uses bounded retries and a reference-video-derived
quality contract. Optional internet research is limited to short public factual /
folklore context; source wording is never copied into the final script.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

import bot
import cloud_v3
import mpt_profile
import mpt_reference_style


def stable_ask(prompt: str, structured: bool = False):
    """Ollama chat with deterministic resource limits and transient retries."""
    payload = {
        "model": os.getenv("KF_STORY_MODEL", "gemma3:4b"),
        "stream": False,
        "keep_alive": "30m",
        "messages": [
            {"role": "system", "content": cloud_v3.SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "num_ctx": 4096,
            "num_predict": 1600,
            "num_thread": 2,
            "temperature": 0.68,
            "repeat_penalty": 1.15,
        },
    }
    if structured:
        payload["format"] = "json"
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error = None
    for attempt, delay in enumerate((0, 8, 18, 30), start=1):
        if delay:
            time.sleep(delay)
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=raw,
            headers={"Content-Type": "application/json"},
        )
        try:
            print(f"Model yaniti bekleniyor ({attempt}/4).", flush=True)
            with urllib.request.urlopen(request, timeout=600) as response:
                result = json.load(response)
            if result.get("done_reason") == "length":
                raise ValueError("Metin token sinirinda kesildi")
            text = str(result["message"]["content"]).strip()
            if not text:
                raise ValueError("Model bos yanit verdi")
            return json.loads(text) if structured else text
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            status = getattr(exc, "code", None)
            print(f"Ollama gecici hata (deneme {attempt}/4, HTTP={status}): {type(exc).__name__}", flush=True)
            try:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=20) as response:
                    response.read(256)
            except Exception:
                pass
    raise RuntimeError(f"Ollama four attempts failed: {type(last_error).__name__}") from last_error


def compose(topic: str, minutes: int, output: Path) -> dict:
    if not 15 <= minutes <= 20:
        raise ValueError("Serious long test target must be 15-20 minutes")
    output.mkdir(parents=True, exist_ok=True)

    research = mpt_reference_style.gather_research(topic)
    (output / "research_sources.json").write_text(
        json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    research_context = mpt_reference_style.research_prompt(research)

    # Reuse the existing planner/editor but strengthen its system contract so
    # chapters feel like grounded testimony rather than generic AI horror.
    cloud_v3.ask = stable_ask
    cloud_v3.SYSTEM = (
        cloud_v3.SYSTEM
        + "\n\n"
        + mpt_reference_style.STYLE_BRIEF
        + "\n\nARAŞTIRMA BAĞLAMI:\n"
        + research_context[:3200]
    )

    title, parts, report = cloud_v3.create_story(topic, minutes, preview=False)
    if len(parts) < 2:
        raise ValueError("Long story did not contain story chapters")

    intro = parts[0].strip()
    chapters = [p.strip() for p in parts[1:] if p.strip()]
    story_only = "\n\n".join(chapters)
    story_check = mpt_profile.check_story(story_only, minutes, preview=False)

    # A separate editorial pass scores the actual result instead of trusting the
    # generator. Low-quality, generic or incoherent stories stop before TTS/render.
    quality_raw = stable_ask(
        mpt_reference_style.quality_prompt(story_only, topic, minutes),
        structured=True,
    )
    quality = mpt_reference_style.validate_quality(quality_raw)
    (output / "reference_style_quality.json").write_text(
        json.dumps({"raw": quality_raw, "validated": quality}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

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
        "reference_style_quality": quality,
        "research": research,
        "editor_report": report,
        "hook_first": True,
        "channel_intro_after_hook": True,
        "internet_research_used": bool(research.get("items")),
        "source_story_copied": False,
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
        "reference_style_score": quality["total"],
        "internet_research_used": state["internet_research_used"],
    }, ensure_ascii=False), flush=True)
    return state


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--output", type=Path, default=Path("output/long-test"))
    args = p.parse_args()
    compose(args.topic, args.minutes, args.output)

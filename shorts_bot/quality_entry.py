"""Quality-gated daily Shorts: original trend-inspired topic, safe visuals and sound."""
from __future__ import annotations

import os

import upgrade
import visual_guard
import selection_guard
import trend_ideas

_original_run = upgrade.bot.run
_original_build = upgrade.aligned_build_video
_original_choose_topic = upgrade.choose_topic
_original_generate_plan = upgrade.generate_plan
_original_model_json = upgrade.model_json


def safe_render(command: list[str]) -> None:
    command = list(command)
    if "-vf" in command:
        position = command.index("-vf") + 1
        if position < len(command) and command[position].startswith("subtitles="):
            command[position] = (command[position]
                                 .replace("FontSize=22", "FontSize=12")
                                 .replace("MarginV=260", "MarginV=70"))
            if "-c:a" in command and "-af" not in command:
                command[command.index("-c:a"):command.index("-c:a")] = [
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11"
                ]
    _original_run(command)


def trend_topic(theme: str) -> str:
    # A fixed test subject is allowed ONLY when uploads are explicitly disabled.
    test_topic = os.getenv("SHORTS_TEST_TOPIC_OVERRIDE", "").strip()
    if test_topic and os.getenv("SHORTS_SKIP_UPLOAD") == "1":
        if not 8 <= len(test_topic) <= 90 or any(c in test_topic for c in "\r\n<>#"):
            upgrade.bot.die("Invalid smoke-test subject")
        print(f"SMOKE TEST: testing visually accessible topic: {test_topic}", flush=True)
        return test_topic
    return trend_ideas.pick_topic(theme, _original_choose_topic, upgrade.model_json)


def trend_plan():
    feedback = ""
    plan = None
    for attempt in range(3):
        def reviewed_model_json(prompt: str):
            if prompt.startswith("You are an English-language, original educational Shorts scriptwriter."):
                prompt += (
                    "\nMANDATORY VISUAL FEASIBILITY: Narrate only things that can clearly be "
                    "shown in real portrait stock footage. Do not require internal anatomy, "
                    "microscopic processes, inaccessible historical reconstructions, or "
                    "invisible changes to be seen; explain mechanisms without pretending "
                    "footage depicts them. Each scene needs three independently matching "
                    "visible moments. Keep every claim scientifically accurate."
                )
                if feedback:
                    prompt += ("\nPREVIOUS DRAFT WAS REJECTED FOR THIS SPECIFIC ERROR: "
                               + feedback + "\nCorrect the factual error and revise the "
                               "surrounding scenes; do not repeat the rejected claim.")
            return _original_model_json(prompt)

        upgrade.model_json = reviewed_model_json
        try:
            plan = _original_generate_plan()
            break
        except SystemExit as exc:
            detail = str(exc)
            marker = "AI editorial check rejected this Short: "
            if marker not in detail or attempt == 2:
                raise
            feedback = detail.split(marker, 1)[1][:600]
            print(f"Editorial review rejected draft {attempt + 1}/3; rewriting with factual feedback.",
                  flush=True)
        finally:
            upgrade.model_json = _original_model_json
    if plan is None:
        upgrade.bot.die("No editor-approved plan; upload cancelled")
    ref = trend_ideas.reference_for(plan["theme"])
    if ref:
        plan["trend_reference"] = ref
    else:
        plan["trend_reference"] = None
        plan["trend_note"] = "No accessible suitable reference or smoke-test topic override"
    return plan


def checked_build(plan, audio_path):
    video = _original_build(plan, audio_path)
    visual_guard.check(plan, upgrade.bot.WORK, video)
    return video


upgrade.bot.run = safe_render
upgrade.choose_topic = trend_topic
upgrade.generate_plan = trend_plan
upgrade.matched_pexels_video = selection_guard.choose
upgrade.aligned_build_video = checked_build

if __name__ == "__main__":
    upgrade.main()

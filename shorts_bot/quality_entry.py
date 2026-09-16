"""Quality-gated daily Shorts: original trend-inspired topic, safe visuals and sound."""
from __future__ import annotations

import upgrade
import visual_guard
import selection_guard
import trend_ideas

_original_run = upgrade.bot.run
_original_build = upgrade.aligned_build_video
_original_choose_topic = upgrade.choose_topic
_original_generate_plan = upgrade.generate_plan


def safe_render(command: list[str]) -> None:
    command = list(command)
    if "-vf" in command:
        position = command.index("-vf") + 1
        if position < len(command) and command[position].startswith("subtitles="):
            # The old ASS font/margin was scaled from 288px and clipped offscreen.
            command[position] = (command[position]
                                 .replace("FontSize=22", "FontSize=12")
                                 .replace("MarginV=260", "MarginV=70"))
            if "-c:a" in command and "-af" not in command:
                command[command.index("-c:a"):command.index("-c:a")] = [
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11"
                ]
    _original_run(command)


def trend_topic(theme: str) -> str:
    # Read public metadata only; all output speech, imagery and editing are new.
    return trend_ideas.pick_topic(theme, _original_choose_topic, upgrade.model_json)


def trend_plan():
    plan = _original_generate_plan()
    ref = trend_ideas.reference_for(plan["theme"])
    if ref:
        plan["trend_reference"] = ref
    else:
        plan["trend_reference"] = None
        plan["trend_note"] = "No accessible suitable reference; evergreen fallback"
    return plan


def checked_build(plan, audio_path):
    video = _original_build(plan, audio_path)
    # Final independently reviewed set: all scenes, three actual frames each.
    visual_guard.check(plan, upgrade.bot.WORK, video)
    return video


upgrade.bot.run = safe_render
upgrade.choose_topic = trend_topic
upgrade.generate_plan = trend_plan
upgrade.matched_pexels_video = selection_guard.choose
upgrade.aligned_build_video = checked_build

if __name__ == "__main__":
    upgrade.main()

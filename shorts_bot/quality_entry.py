"""Quality-gated daily production: preselect clips, safe captions, loud voice."""
from __future__ import annotations

import upgrade
import visual_guard
import selection_guard

_original_run = upgrade.bot.run
_original_build = upgrade.aligned_build_video


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


def checked_build(plan, audio_path):
    video = _original_build(plan, audio_path)
    # Final independently reviewed set: all scenes, three actual frames each.
    visual_guard.check(plan, upgrade.bot.WORK, video)
    return video


upgrade.bot.run = safe_render
upgrade.matched_pexels_video = selection_guard.choose
upgrade.aligned_build_video = checked_build

if __name__ == "__main__":
    upgrade.main()

"""Production entrypoint: correct subtitle safe-area and require actual-frame review."""
from __future__ import annotations

import upgrade
import visual_guard

_original_run = upgrade.bot.run
_original_build = upgrade.aligned_build_video


def safe_render(command: list[str]) -> None:
    """Fix ASS's 288px reference-frame scaling that previously clipped top captions."""
    command = list(command)
    if "-vf" in command:
        position = command.index("-vf") + 1
        if position < len(command) and command[position].startswith("subtitles="):
            command[position] = (command[position]
                                 .replace("FontSize=22", "FontSize=12")
                                 .replace("MarginV=260", "MarginV=70"))
    _original_run(command)


def checked_build(plan, audio_path):
    video = _original_build(plan, audio_path)
    visual_guard.check(plan, upgrade.bot.WORK, video)
    return video


upgrade.bot.run = safe_render
upgrade.aligned_build_video = checked_build

if __name__ == "__main__":
    upgrade.main()

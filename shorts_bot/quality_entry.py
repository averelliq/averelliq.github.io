"""Production entrypoint: caption-safe render, voice normalization, visual review."""
from __future__ import annotations

import upgrade
import visual_guard

_original_run = upgrade.bot.run
_original_build = upgrade.aligned_build_video


def safe_render(command: list[str]) -> None:
    """Correct subtitle scaling and normalize speech in the final render only."""
    command = list(command)
    if "-vf" in command:
        position = command.index("-vf") + 1
        if position < len(command) and command[position].startswith("subtitles="):
            # ASS style units are scaled from a small reference frame; the old
            # FontSize=22, MarginV=260 placed huge captions above the top edge.
            command[position] = (command[position]
                                 .replace("FontSize=22", "FontSize=12")
                                 .replace("MarginV=260", "MarginV=70"))
            # The previous videos had mean audio levels near -28 dBFS. Limit
            # true peaks and target a consistent spoken-word loudness.
            if "-c:a" in command and "-af" not in command:
                command[command.index("-c:a"):command.index("-c:a")] = [
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11"
                ]
    _original_run(command)


def checked_build(plan, audio_path):
    video = _original_build(plan, audio_path)
    # Fail closed: never upload if any selected clip is duplicated or the
    # vision review sees mismatched imagery. An AI review is not infallible.
    visual_guard.check(plan, upgrade.bot.WORK, video)
    return video


upgrade.bot.run = safe_render
upgrade.aligned_build_video = checked_build

if __name__ == "__main__":
    upgrade.main()

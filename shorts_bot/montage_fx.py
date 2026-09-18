"""Original soundtrack, animated captions and subtle motion for cloud Shorts.

The subject-matching stock picker and fail-closed visual review are unchanged.
This module never invokes the YouTube uploader.
"""
from __future__ import annotations

import math
import os
import re
import wave
from pathlib import Path

import numpy as np

CLIP_NAME = re.compile(r"^clip_(\d{2})\.mp4$")


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, rem = divmod(centiseconds, 360000)
    minutes, rem = divmod(rem, 6000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ")


def write_animated_captions(plan: dict, destination: Path) -> None:
    """Scene-timed four-word cues with a fade; not forced-word alignment."""
    scenes = plan["scenes"]
    durations = plan["scene_durations"]
    if len(scenes) != len(durations) or not scenes:
        raise ValueError("Caption scenes and actual speech durations differ")
    header = """[Script Info]
Title: Original Shorts scene-timed captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Captions,DejaVu Sans,61,&H00FFFFFF,&H00FFFFFF,&H00101925,&H78000000,-1,0,0,0,100,100,0,0,1,4,1,2,85,85,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    cursor = 0.0
    for scene_index, (scene, duration) in enumerate(zip(scenes, durations)):
        words = str(scene["voiceover"]).split()
        if not words or not 0 < float(duration) < 90:
            raise ValueError("Invalid caption narration or duration")
        groups = [words[i:i + 4] for i in range(0, len(words), 4)]
        weights = [sum(max(1, len(word)) for word in group) for group in groups]
        total_weight = sum(weights)
        elapsed = 0.0
        for group_index, (group, weight) in enumerate(zip(groups, weights)):
            start = cursor + elapsed
            elapsed += float(duration) * weight / total_weight
            end = cursor + (float(duration) if group_index == len(groups) - 1 else elapsed)
            accent = "\\c&H00B4EAFF&" if scene_index == group_index == 0 else ""
            caption = _ass_escape(" ".join(group))
            lines.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Captions,,0,0,0,,"
                f"{{\\fad(110,90){accent}}}{caption}\n"
            )
        cursor += float(duration)
    destination.write_text("".join(lines), encoding="utf-8")


def make_original_music(path: Path, duration: float, scene_durations: list[float]) -> None:
    """Synthesize a quiet original ambient bed without a third-party recording."""
    sample_rate = 24000
    if not 20 <= duration <= 65:
        raise ValueError("Music length outside supported Shorts duration")
    count = int(math.ceil((duration + 0.25) * sample_rate))
    t = np.arange(count, dtype=np.float32) / sample_rate
    frequencies = (110.0, 164.81, 196.0, 261.63)
    pad = sum(
        (0.25 / (index + 1)) * np.sin((2 * np.pi * frequency * t) + index * .47)
        for index, frequency in enumerate(frequencies)
    )
    swell = 0.67 + 0.23 * np.sin(2 * np.pi * 0.16 * t) ** 2
    audio = (pad * swell * 0.42).astype(np.float32)
    rng = np.random.default_rng(70531)
    at = 0.0
    for scene_seconds in scene_durations[:-1]:
        at += float(scene_seconds)
        width = int(sample_rate * 0.14)
        start = int((at - 0.07) * sample_rate)
        if start < 0 or start + width > count:
            continue
        noise = rng.standard_normal(width).astype(np.float32)
        noise[1:] -= noise[:-1] * 0.94
        envelope = np.sin(np.linspace(0, math.pi, width, dtype=np.float32)) ** 2
        audio[start:start + width] += 0.008 * noise * envelope
    fade = min(int(sample_rate * .65), count // 4)
    audio[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
    audio[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    peak = float(np.max(np.abs(audio)))
    if not np.isfinite(peak) or peak == 0:
        raise ValueError("Generated audio was invalid")
    pcm = np.asarray(np.clip(audio, -0.95, 0.95) * 32767, dtype="<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def enhance_command(command: list[str], run_original, state: dict) -> None:
    """Enhance only known ffmpeg clip/final commands and preserve all others."""
    cmd = list(command)
    if not cmd or cmd[0] != "ffmpeg":
        return run_original(cmd)
    clip = CLIP_NAME.fullmatch(Path(cmd[-1]).name)
    if clip and "-vf" in cmd:
        filter_index = cmd.index("-vf") + 1
        current = cmd[filter_index]
        if current.startswith("scale=1080:1920:") and "crop=1080:1920" in current:
            scene = int(clip.group(1))
            cmd[filter_index] = (
                "scale=1166:2073:force_original_aspect_ratio=increase,"
                "crop=1080:1920:"
                f"x='(in_w-out_w)/2+(in_w-out_w)*0.16*sin(t*0.60+{scene})':"
                f"y='(in_h-out_h)/2+(in_h-out_h)*0.12*cos(t*0.48+{scene})',"
                "eq=contrast=1.035:saturation=1.075,fps=30,setsar=1"
            )
            state["motion_clips"] += 1
        return run_original(cmd)
    if Path(cmd[-1]).name != "short.mp4" or "-vf" not in cmd:
        return run_original(cmd)
    filter_index = cmd.index("-vf") + 1
    subtitles = cmd[filter_index]
    srt = state.get("srt")
    ass = state.get("ass")
    if srt and ass and srt in subtitles and ass.is_file():
        cmd[filter_index] = f"subtitles={ass.as_posix()}"
        state["animated_captions"] = True
    if not state.get("music_enabled", True):
        return run_original(cmd)
    path = state.get("music")
    if not isinstance(path, Path) or not path.is_file():
        raise ValueError("Original music file missing; publishing blocked")
    if cmd.count("-i") != 2 or "-filter_complex" in cmd:
        raise ValueError("Unexpected final render command; cannot safely add music")
    if "-af" in cmd:
        pos = cmd.index("-af")
        del cmd[pos:pos + 2]
    gain = float(os.getenv("SHORTS_MUSIC_GAIN", "0.20"))
    if not 0.0 <= gain <= 0.30 or not math.isfinite(gain):
        raise ValueError("SHORTS_MUSIC_GAIN must be between 0 and 0.30")
    cmd[cmd.index("-vf"):cmd.index("-vf")] = ["-i", str(path)]
    cmd += ["-map", "0:v:0", "-map", "[aout]", "-filter_complex",
            "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[voice];"
            f"[2:a]volume={gain:.3f}[music];"
            "[voice][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.95[aout]"]
    output = cmd.pop(cmd.index(command[-1]))
    cmd.append(output)
    state["original_music"] = True
    return run_original(cmd)


def install(quality_module) -> dict:
    """Attach editing improvements without changing the uploader or stock guards."""
    import upgrade

    if not callable(getattr(quality_module, "_original_run", None)):
        raise ValueError("Quality entrypoint does not expose a renderer")
    original_run = quality_module._original_run
    original_subtitles = upgrade.aligned_subtitles
    state = {"motion_clips": 0, "animated_captions": False,
             "original_music": False, "music_enabled": os.getenv("SHORTS_MUSIC", "1") != "0"}

    def captions_with_animation(plan: dict, path: Path) -> None:
        original_subtitles(plan, path)
        ass = path.with_suffix(".ass")
        write_animated_captions(plan, ass)
        state["srt"] = path.as_posix()
        state["ass"] = ass
        if state["music_enabled"]:
            music = path.with_name("original_music.wav")
            make_original_music(music, float(plan["audio_duration"]), plan["scene_durations"])
            state["music"] = music

    def rendered(command: list[str]) -> None:
        return enhance_command(command, original_run, state)

    upgrade.aligned_subtitles = captions_with_animation
    quality_module._original_run = rendered
    return state

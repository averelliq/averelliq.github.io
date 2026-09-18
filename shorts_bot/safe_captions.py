"""Phone-safe, single-layer captions for filmed Shorts; never overlays a title."""
from __future__ import annotations

import re
from pathlib import Path

import montage_fx

MAX_CHARS = 19
MAX_WORDS = 3


def cues(words: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    for word in words:
        if len(word) > MAX_CHARS:
            raise ValueError("Narration includes an oversized unbreakable caption word")
        next_group = [*current, word]
        if current and (len(next_group) > MAX_WORDS or len(" ".join(next_group)) > MAX_CHARS):
            groups.append(current)
            current = [word]
        else:
            current = next_group
    if current:
        groups.append(current)
    return groups


def write(plan: dict, destination: Path) -> None:
    scenes = plan["scenes"]
    durations = plan["scene_durations"]
    if not scenes or len(scenes) != len(durations):
        raise ValueError("Captions do not match spoken scenes")
    header = """[Script Info]
Title: Phone-safe Shorts captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Captions,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00101925,&H78000000,-1,0,0,0,100,100,0,0,1,4,1,2,135,135,345,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [header]
    cursor = 0.0
    for scene_index, (scene, seconds) in enumerate(zip(scenes, durations)):
        duration = float(seconds)
        if not 0 < duration < 90:
            raise ValueError("Invalid caption duration")
        groups = cues(str(scene["voiceover"]).split())
        if not groups:
            raise ValueError("Missing spoken caption words")
        weights = [sum(max(1, len(word)) for word in group) for group in groups]
        total = sum(weights)
        elapsed = 0.0
        for index, (group, weight) in enumerate(zip(groups, weights)):
            start = cursor + elapsed
            elapsed += duration * weight / total
            end = cursor + (duration if index == len(groups) - 1 else elapsed)
            text = montage_fx._ass_escape(" ".join(group))
            if len(" ".join(group)) > MAX_CHARS:
                raise ValueError("Caption line overflow")
            accent = "\\c&H00B4EAFF&" if scene_index == index == 0 else ""
            events.append(f"Dialogue: 0,{montage_fx._ass_time(start)},{montage_fx._ass_time(end)},Captions,,0,0,0,,{{\\fad(80,70){accent}}}{text}\n")
        cursor += duration
    destination.write_text("".join(events), encoding="utf-8")
    text = destination.read_text(encoding="utf-8")
    if len([line for line in text.splitlines() if line.startswith("Dialogue:")]) < sum(len(cues(scene["voiceover"].split())) for scene in scenes):
        raise ValueError("Caption cues unexpectedly missing")


def install() -> None:
    montage_fx.write_animated_captions = write

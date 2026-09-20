"""Small, silent like/subscribe reminder over real Shorts footage.

Adds one ASS subtitle event to the existing caption track. No extra duration,
voice interruption, external media, or YouTube API calls.
"""
from __future__ import annotations

import os
from pathlib import Path


def _ass_time(seconds: float) -> str:
    centis = max(0, int(round(seconds * 100)))
    hours, rest = divmod(centis, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, hundredths = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{hundredths:02d}"


def add_reminder(ass_path: Path, duration: float) -> tuple[float, float]:
    """Insert one top-centre CTA above bottom-aligned narration captions."""
    if not ass_path.is_file():
        raise ValueError("Caption track missing; cannot add CTA")
    if not 20.0 <= duration <= 65.0:
        raise ValueError("Invalid video duration for CTA")
    text = ass_path.read_text(encoding="utf-8")
    if "Style: Reminder," in text or "REMINDER_ADDED" in text:
        raise ValueError("CTA already present; refusing duplicated overlay")
    styles_marker = "[Events]\n"
    if styles_marker not in text or "Style: Captions," not in text:
        raise ValueError("Unexpected ASS subtitle layout; cannot safely add CTA")
    # At 68% of spoken duration; keep the final answer/reveal unobstructed.
    start = min(duration * 0.68, duration - 4.0)
    end = start + 2.0
    style = (
        "Style: Reminder,DejaVu Sans,51,&H00FFFFFF,&H00FFFFFF,"
        "&H00232936,&H660E1622,-1,0,0,0,100,100,0,0,3,0,0,8,55,55,260,1\n"
    )
    text = text.replace(styles_marker, style + "\n" + styles_marker, 1)
    text += (
        f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},Reminder,,0,0,0,,"
        "{\\fad(200,250)}LIKE  +  SUBSCRIBE\n"
    )
    ass_path.write_text(text, encoding="utf-8")
    print(f"CTA OVERLAY: silent LIKE + SUBSCRIBE from {start:.2f}s to {end:.2f}s", flush=True)
    return start, end


def install(quality_module, state: dict) -> None:
    """Hook the final render, after montage_fx created the ASS subtitle file."""
    if os.getenv("SHORTS_CTA", "1") == "0":
        state["cta_overlay"] = False
        return
    original_run = quality_module._original_run
    if not callable(original_run):
        raise ValueError("Renderer unavailable; cannot install CTA")
    state["cta_overlay"] = False
    def rendered(command: list[str]):
        if command and command[0] == "ffmpeg" and Path(command[-1]).name == "short.mp4":
            ass = state.get("ass")
            if not isinstance(ass, Path):
                raise ValueError("Animated caption path missing for CTA")
            # The ASS track is generated before the final ffmpeg invocation.
            import upgrade
            plan = upgrade.CURRENT_PLAN
            if not isinstance(plan, dict):
                raise ValueError("Finalized plan missing for CTA")
            add_reminder(ass, float(plan["audio_duration"]))
            state["cta_overlay"] = True
        return original_run(command)
    quality_module._original_run = rendered

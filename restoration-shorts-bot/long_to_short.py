#!/usr/bin/env python3
"""Chronological long-form restoration -> <=60s vertical Short (no paid APIs)."""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_SCRIPT = (
    "Watch this restoration from beginning to end. "
    "First, take a look at the original condition. "
    "Now watch the cleaning and careful hands-on work unfold. "
    "Every part of the process stays in its original order; "
    "the footage is sped up, not rearranged. "
    "Keep watching to see how the finished result compares with the start."
)
CTA_SCRIPT = "Enjoyed the restoration? Hit like and subscribe for more!"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def execute(command: list[str]) -> None:
    print("$ " + " ".join(command[:3]) + " ...", flush=True)
    subprocess.run(command, check=True)


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def media_duration(data: dict) -> float:
    raw = data.get("format", {}).get("duration")
    if raw is None:
        raise ValueError("Input duration is unavailable; provide a normal MP4/MOV video.")
    duration = float(raw)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Input duration must be a positive finite number.")
    return duration


def parse_subtitle_box(box: str, width: int, height: int) -> str | None:
    """Optional exact input-pixel rectangle to conceal permanently embedded subtitles."""
    if not box or box.lower() == "none":
        return None
    try:
        x, y, w, h = map(int, box.split(":"))
    except (ValueError, TypeError):
        raise ValueError("--subtitle-box must be none or x:y:width:height in source pixels") from None
    if x < 0 or y < 0 or w < 8 or h < 8 or x + w > width or y + h > height:
        raise ValueError(f"Subtitle box must fit the source's {width}x{height} frame.")
    return f"delogo=x={x}:y={y}:w={w}:h={h}"


def build_filter(duration: float, target: float, subtitle_box: str | None) -> str:
    """Keep the entire original time range; blur-fill the sides instead of cropping the subject."""
    speed = duration / target
    initial = f"{subtitle_box}," if subtitle_box else ""
    video = (
        f"[0:v:0]{initial}split=2[background][foreground];"
        "[background]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=18:1[blur];"
        "[foreground]scale=1080:1920:force_original_aspect_ratio=decrease[sharp];"
        "[blur][sharp]overlay=(W-w)/2:(H-h)/2,setsar=1,"
        f"setpts=(PTS-STARTPTS)/{speed:.12f},fps=30,"
        f"trim=duration={target:.6f},format=yuv420p[v]"
    )
    return video


def make_video(source: Path, output: Path, duration: float, target: float, box: str | None) -> None:
    # Burned-in subtitles are pixels: an optional rectangular delogo is approximate.
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-filter_complex", build_filter(duration, target, box), "-map", "[v]",
        "-an", "-sn", "-dn", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", str(target), str(output),
    ]
    execute(command)


async def synthesize(text: str, voice: str, destination: Path) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Missing edge-tts. Install requirements.txt on the runner.") from exc
    await edge_tts.Communicate(text=text, voice=voice).save(str(destination))
    if not destination.exists() or destination.stat().st_size < 100:
        raise RuntimeError("English voice synthesis returned an empty audio file.")


def make_audio(narration: Path, cta: Path, output: Path, target: float) -> None:
    narration_length = media_duration(probe(narration))
    cta_length = media_duration(probe(cta))
    cta_start = max(0.0, target - cta_length - 0.4)
    if narration_length + 1.0 > cta_start:
        raise ValueError(
            f"Narration is {narration_length:.1f}s; shorten it to under "
            f"{max(0.0, cta_start - 1):.1f}s so the spoken CTA has its own space."
        )
    delay_ms = round(cta_start * 1000)
    filters = (
        "[0:a]asetpts=PTS-STARTPTS[n];"
        f"[1:a]asetpts=PTS-STARTPTS,adelay={delay_ms}:all=1[c];"
        f"[n][c]amix=inputs=2:duration=longest:dropout_transition=0,"
        f"apad,atrim=duration={target:.6f}[a]"
    )
    execute([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(narration),
        "-i", str(cta), "-filter_complex", filters, "-map", "[a]",
        "-c:a", "aac", "-b:a", "160k", str(output),
    ])


def combine(video: Path, audio: Path, output: Path, target: float) -> None:
    # Add the CTA in the final seconds, not across restoration details.
    cta_start = max(0.0, target - 7.0)
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not Path(font).exists():
        raise FileNotFoundError(f"CTA font not available: {font}")
    drawtext = (
        f"drawtext=fontfile={font}:text='LIKE + SUBSCRIBE':fontcolor=white:fontsize=52:"
        "box=1:boxcolor=black@0.72:boxborderw=24:"
        f"x=(w-text_w)/2:y=h-270:enable='between(t,{cta_start:.3f},{target:.3f})'"
    )
    execute([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
        "-i", str(audio), "-vf", drawtext, "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", "-t", str(target), str(output),
    ])


def validate_final(path: Path, target: float) -> dict:
    data = probe(path)
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    subtitles = [s for s in streams if s.get("codec_type") == "subtitle"]
    length = media_duration(data)
    if len(videos) != 1 or int(videos[0]["width"]) != 1080 or int(videos[0]["height"]) != 1920:
        raise RuntimeError("QA failed: expected one 1080x1920 video stream.")
    if len(audios) != 1 or subtitles:
        raise RuntimeError("QA failed: expected exactly one new audio stream and no subtitle streams.")
    if not 0 < length <= 60.0 or abs(length - target) > 0.7:
        raise RuntimeError(f"QA failed: output length is {length:.3f}s, expected {target:.3f}s.")
    if path.stat().st_size < 1000:
        raise RuntimeError("QA failed: output file is unexpectedly small.")
    return {"duration_seconds": round(length, 3), "width": 1080, "height": 1920,
            "has_english_voice_track": True, "subtitle_streams": 0, "bytes": path.stat().st_size}


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=Path("output/report.json"))
    parser.add_argument("--narration", default=DEFAULT_SCRIPT)
    parser.add_argument("--voice", default="en-US-AndrewNeural")
    parser.add_argument("--subtitle-box", default="none")
    parser.add_argument("--target", type=float, default=59.9)
    parser.add_argument("--narration-audio", type=Path, help="Optional offline narration file for testing")
    parser.add_argument("--cta-audio", type=Path, help="Optional offline CTA file for testing")
    args = parser.parse_args(argv)
    report: dict = {"stage": "starting", "stage_history": [], "source_audio_policy": "removed entirely"}

    def stage(name: str) -> None:
        report["stage"] = name
        report["stage_history"].append(name)
        write_report(args.report, report)
        print(f"::group::{name}", flush=True)

    def done() -> None:
        print("::endgroup::", flush=True)

    try:
        stage("01 / Validate supplied video")
        if not args.input.is_file() or args.input.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError("Input must be an existing .mp4/.mov/.mkv/.webm/.m4v video.")
        if not 1 <= args.target <= 59.9:
            raise ValueError("Target must be between 1 and 59.9 seconds.")
        data = probe(args.input)
        videos = [s for s in data["streams"] if s.get("codec_type") == "video"]
        if not videos:
            raise ValueError("The input has no video stream.")
        duration = media_duration(data)
        target = min(duration, args.target)
        speed = duration / target
        report.update({"source_duration_seconds": round(duration, 3),
                       "target_seconds": round(target, 3), "speed_multiplier": round(speed, 5),
                       "timeline_policy": "every source moment remains in chronological order (speed-up)",
                       "original_audio_present": any(s.get("codec_type") == "audio" for s in data["streams"]),
                       "original_subtitle_streams": sum(s.get("codec_type") == "subtitle" for s in data["streams"])})
        box = parse_subtitle_box(args.subtitle_box, int(videos[0]["width"]), int(videos[0]["height"]))
        report["burned_in_subtitles"] = "approximate delogo rectangle" if box else "not removed unless a rectangle is supplied"
        done()

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="restoration-") as temporary:
            work = Path(temporary)
            stage("02 / Render entire chronological video at 1080x1920")
            silent_video = work / "silent.mp4"
            make_video(args.input, silent_video, duration, target, box)
            done()

            stage("03 / Create natural English narration and spoken like/subscribe CTA")
            narr = work / "narration.mp3"
            cta = work / "cta.mp3"
            if args.narration_audio:
                shutil.copyfile(args.narration_audio, narr)
            else:
                asyncio.run(synthesize(args.narration, args.voice, narr))
            if args.cta_audio:
                shutil.copyfile(args.cta_audio, cta)
            else:
                asyncio.run(synthesize(CTA_SCRIPT, args.voice, cta))
            narration_duration = media_duration(probe(narr))
            report["voice"] = args.voice
            report["narration_length_seconds"] = round(narration_duration, 3)
            done()

            stage("04 / Mix English narration only; discard all original speech/music")
            clean_audio = work / "clean.m4a"
            make_audio(narr, cta, clean_audio, target)
            done()

            stage("05 / Add visual CTA and finish vertical MP4")
            combine(silent_video, clean_audio, args.output, target)
            done()

            stage("06 / Verify duration, aspect ratio, audio and subtitle tracks")
            report["qa"] = validate_final(args.output, target)
            report["stage"] = "complete"
            done()
        write_report(args.report, report)
        print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        report["stage"] = "failed"
        report["error"] = str(exc)
        write_report(args.report, report)
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
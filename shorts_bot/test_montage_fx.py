"""Credential-free integration smoke test: no YouTube or external AI calls."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import montage_fx as fx


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(
            f"FFmpeg render failed: {result.stderr[-2200:]}\n"
            f"Command: {' '.join(command)}"
        )


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        script = {"scenes": [{"voiceover": "What makes this idea look so different now?"}],
                  "scene_durations": [4.0]}
        captions = root / "captions.ass"
        fx.write_animated_captions(script, captions)
        text = captions.read_text(encoding="utf-8")
        assert "Dialogue:" in text and "What makes this" in text
        assert "MarginV, Encoding" in text and "\\fad(110,90)" in text
        music = root / "original_music.wav"
        fx.make_original_music(music, 22.0, [4.0, 4.0, 4.0])
        assert music.stat().st_size > 100_000

        source = root / "source.mp4"
        clip = root / "clip_00.mp4"
        silent = root / "silent.mp4"
        voice = root / "voice.wav"
        final = root / "short.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             "testsrc2=size=540x960:rate=24:duration=2", "-c:v", "libx264",
             "-preset", "ultrafast", str(source)])
        state = {"motion_clips": 0, "srt": (root / "captions.srt").as_posix(),
                 "ass": captions, "music": music, "music_enabled": True,
                 "original_music": False, "animated_captions": False}
        fx.enhance_command([
            "ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(source),
            "-t", "4.00", "-an", "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "29",
            "-pix_fmt", "yuv420p", str(clip),
        ], run, state)
        assert state["motion_clips"] == 1
        run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-c", "copy", str(silent)])
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             "sine=frequency=200:duration=4:sample_rate=24000", "-acodec", "pcm_s16le", str(voice)])
        fx.enhance_command([
            "ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(voice),
            "-vf", f"subtitles={(root / 'captions.srt').as_posix()}:force_style='FontSize=12'",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac",
            "-b:a", "96k", "-shortest", "-movflags", "+faststart", str(final),
        ], run, state)
        metadata = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(final)
        ]))
        assert state["animated_captions"] and state["original_music"]
        assert len(metadata["streams"]) == 2
        assert 3.5 < float(metadata["format"]["duration"]) < 4.5
        assert {item["codec_type"] for item in metadata["streams"]} == {"video", "audio"}
        print("PASS: animated captions + original soundtrack + moving stock + real MP4 audio/video")
        print("PASS: smoke test uses no credentials, network requests or YouTube upload")


if __name__ == "__main__":
    main()

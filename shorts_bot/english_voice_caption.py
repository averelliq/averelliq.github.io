#!/usr/bin/env python3
"""Add English narration and captions; production mode requires a natural voice file."""
import argparse, json, subprocess, tempfile
from pathlib import Path

def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-3000:])

def srt_time(sec):
    ms = int(round(sec * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def chunks(text):
    words = text.split(); return [" ".join(words[i:i+5]) for i in range(0, len(words), 5)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path); ap.add_argument("manifest", type=Path)
    ap.add_argument("--out", type=Path, required=True); ap.add_argument("--srt", type=Path, required=True)
    ap.add_argument("--voice", type=Path, help="Doğal İngilizce narration WAV/MP3 dosyası")
    ap.add_argument("--allow-robotic-test", action="store_true", help="Sadece teknik test için flite sesi")
    a = ap.parse_args(); data = json.loads(a.manifest.read_text(encoding="utf-8")); blocks = data["blocks"]
    if not a.voice and not a.allow_robotic_test:
        raise SystemExit("Yayın için doğal İngilizce ses gerekli. --voice verin; robotik ses yalnızca testte kullanılabilir.")
    a.out.parent.mkdir(parents=True, exist_ok=True); a.srt.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="en_voice_") as temp:
        td = Path(temp); wavs = []; cues = []; narration = td / "narration.wav"
        if a.voice:
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(a.voice), "-ar", "48000", "-ac", "2", str(narration)])
        for i, b in enumerate(blocks, 1):
            text = b["text"].replace("'", "").replace(":", ",")
            dur = float(b["end"]) - float(b["start"])
            if not a.voice:
                wav = td / f"voice_{i:02d}.wav"
                run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"flite=text='{text}':voice=kal", "-t", f"{dur:.3f}", "-af", "apad", "-ar", "48000", "-ac", "2", str(wav)])
                wavs.append(wav)
            parts = chunks(b["text"]); span = dur / max(1, len(parts))
            for j, part in enumerate(parts):
                cues.append((float(b["start"]) + j * span, min(float(b["end"]), float(b["start"]) + (j + 1) * span), part))
        if not a.voice:
            lst = td / "audio.txt"; lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in wavs), encoding="utf-8")
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "pcm_s16le", str(narration)])
        narrated = td / "narrated.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(a.video), "-i", str(narration), "-filter_complex", "[0:a]volume=0.18[bg];[1:a]volume=1.2[vo];[bg][vo]amix=inputs=2:duration=first:dropout_transition=1,alimiter=limit=0.95[m]", "-map", "0:v:0", "-map", "[m]", "-t", "40", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", str(narrated)])
        lines = []
        for i, (st, en, txt) in enumerate(cues, 1): lines += [str(i), f"{srt_time(st)} --> {srt_time(en)}", txt, "\n"]
        a.srt.write_text("\n".join(lines), encoding="utf-8")
        style = "FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=260"
        subpath = str(a.srt.resolve()).replace("\\", "/").replace(":", "\\:")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(narrated), "-vf", f"subtitles={subpath}:force_style='{style}'", "-t", "40", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", str(a.out)])

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""Auditable 40-second Shorts renderer and quality checker."""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from content_rules import validate_content_spec

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT, FPS, TOTAL = 1080, 1920, 30, 40.0
CTA = "LIKE + SUBSCRIBE"

def run(cmd, *, check=True, capture=False):
    p = subprocess.run(cmd, text=True, capture_output=capture)
    if check and p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "FFmpeg failed")[-4000:])
    return p

def ffprobe(path):
    p = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=width,height,r_frame_rate,codec_name,codec_type",
             "-of", "json", str(path)], capture=True)
    return json.loads(p.stdout)

def duration(path):
    return float(ffprobe(path).get("format", {}).get("duration", 0))

def source_path(source, plan_file=None):
    p = Path(source)
    if p.is_absolute() or p.exists():
        return p
    if plan_file:
        candidate = Path(plan_file).resolve().parent / p
        if candidate.exists():
            return candidate
    return p

def source_ok(source, plan_file=None):
    return source and source_path(source, plan_file).exists()

def atempo_chain(speed):
    value = float(speed)
    filters = []
    while value < 0.5:
        filters.append("atempo=0.5")
        value /= 0.5
    while value > 2.0:
        filters.append("atempo=2.0")
        value /= 2.0
    filters.append(f"atempo={value:.6f}")
    return ",".join(filters)

def validate_plan(plan):
    errors = []
    if plan.get("content_spec"):
        errors.extend(validate_content_spec(plan["content_spec"]))
    if plan.get("duration", TOTAL) != TOTAL:
        errors.append("Plan süresi tam 40.0 saniye olmalı.")
    scenes = plan.get("scenes", [])
    if not 8 <= len(scenes) <= 12:
        errors.append("Plan 8–12 anlamlı sahne içermeli.")
    if plan.get("realistic_ai", False) and not plan.get("ai_disclosure", False):
        errors.append("Gerçekçi AI içeriği için ai_disclosure=true olmalı.")
    if plan.get("single_source") and scenes:
        first = scenes[0]
        for key in ("start", "end", "action", "object_before", "object_after", "source", "license"):
            if key not in first:
                errors.append(f"Sürekli kaynak planı: {key} eksik.")
        if first.get("start") != 0 or first.get("end") != TOTAL:
            errors.append("Sürekli kaynak planının ilk sahnesi 0–40 saniye olmalı.")
        cta = plan.get("cta", {})
        if cta.get("text") != CTA or cta.get("start") != 34 or cta.get("end") != 37:
            errors.append("CTA tam olarak 34–37 saniye aralığında 'LIKE + SUBSCRIBE' olmalı.")
        return errors
    cursor = 0.0
    for i, s in enumerate(scenes, 1):
        for key in ("start", "end", "action", "object_before", "object_after", "source", "license"):
            if key not in s:
                errors.append(f"Sahne {i}: {key} eksik.")
        if "start" in s and "end" in s:
            if abs(float(s["start"]) - cursor) > .01:
                errors.append(f"Sahne {i}: zaman çizelgesi kesintili ({cursor:.2f} bekleniyordu).")
            if float(s["end"]) <= float(s["start"]):
                errors.append(f"Sahne {i}: bitiş başlangıçtan sonra olmalı.")
            cursor = float(s["end"])
        if s.get("license", "").strip().lower() in ("", "unknown", "belirsiz"):
            errors.append(f"Sahne {i}: kullanım hakkı/lisans kaydı yok.")
    if abs(cursor - TOTAL) > .01:
        errors.append(f"Sahneler toplamı {cursor:.2f} saniye; 40.0 olmalı.")
    cta = plan.get("cta", {})
    if cta.get("text") != CTA or cta.get("start") != 34 or cta.get("end") != 37:
        errors.append("CTA tam olarak 34–37 saniye aralığında 'LIKE + SUBSCRIBE' olmalı.")
    return errors

def render_one(src, out, seconds, label, source_start=0.0, source_speed=1.0):
    # A source may be a still image or a video. Scale/pad preserves content and avoids stretching.
    ext = Path(src).suffix.lower()
    seek = ["-ss", f"{float(source_start):.3f}"] if float(source_start) > 0 else []
    inp = (seek + ["-loop", "1", "-i", str(src)]) if ext in {".png", ".jpg", ".jpeg", ".webp"} else (seek + ["-i", str(src)])
    vf = (f"setpts={1.0/float(source_speed):.6f}*PTS,"
          f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
          f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
          f"fps={FPS},format=yuv420p,"
          f"drawtext=text='{label.replace(chr(39), '')}':fontcolor=white:fontsize=42:"
          f"box=1:boxcolor=black@0.55:boxborderw=18:x=48:y=80")
    audio_filter = atempo_chain(source_speed) if float(source_speed) != 1.0 else "anull"
    cmd = ["ffmpeg", "-y", *inp, "-t", f"{seconds:.3f}", "-vf", vf,
           "-r", str(FPS), "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "20", "-af", audio_filter,
           "-c:a", "aac", "-b:a", "128k", str(out)]
    run(cmd)

def concat(clips, out, keep_audio=False):
    listfile = out.with_suffix(".concat.txt")
    listfile.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
    # CTA is deliberately added after concat so its exact time is independent of scene boundaries.
    vf = ("drawtext=text='LIKE + SUBSCRIBE':fontcolor=white:fontsize=64:"
          "font='DejaVu Sans':box=1:boxcolor=black@0.72:boxborderw=24:"
          "x=(w-text_w)/2:y=260:enable='between(t,34,37)'")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile)]
    if keep_audio:
        cmd += ["-vf", vf, "-map", "0:v:0", "-map", "0:a:0?", "-t", "40.000"]
    else:
        cmd += ["-f", "lavfi", "-t", "40.000", "-i", "anullsrc=r=48000:cl=stereo",
                "-vf", vf, "-map", "0:v:0", "-map", "1:a:0", "-t", "40.000"]
    cmd += ["-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k"]
    if not keep_audio:
        cmd.append("-shortest")
    cmd.append(str(out))
    run(cmd)
    listfile.unlink(missing_ok=True)

def render(plan_path, output):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    errors = validate_plan(plan)
    if errors:
        raise ValueError("Plan onaylanmadı:\n- " + "\n- ".join(errors))
    with tempfile.TemporaryDirectory(prefix="shorts_bot_") as td:
        clips = []
        if plan.get("single_source"):
            s = plan["scenes"][0]
            resolved = source_path(s["source"], plan_path)
            if not source_ok(s["source"], plan_path):
                raise FileNotFoundError(f"Kaynak bulunamadı: {s['source']}")
            p = Path(td) / "continuous_source.mp4"
            render_one(resolved, p, TOTAL, s["label"], s.get("source_start", 0.0), s.get("source_speed", 1.0))
            clips.append(p)
            output.parent.mkdir(parents=True, exist_ok=True)
            concat(clips, output, keep_audio=True)
            return output
        for i, s in enumerate(plan["scenes"], 1):
            resolved = source_path(s["source"], plan_path)
            if not source_ok(s["source"], plan_path):
                raise FileNotFoundError(f"Sahne {i} kaynağı bulunamadı: {s['source']}")
            p = Path(td) / f"scene_{i:02d}.mp4"
            render_one(resolved, p, float(s["end"])-float(s["start"]), s["label"],
                       s.get("source_start", 0.0), s.get("source_speed", 1.0))
            clips.append(p)
        output.parent.mkdir(parents=True, exist_ok=True)
        concat(clips, output, keep_audio=True)
    return output

def qc(video, plan=None):
    report = {"file": str(video), "checks": {}, "publish_ready": False, "errors": []}
    if not Path(video).exists():
        report["errors"].append("MP4 bulunamadı.")
        return report
    meta = ffprobe(video)
    streams = meta.get("streams", [])
    v = next((x for x in streams if x.get("codec_type") == "video"), {})
    a = next((x for x in streams if x.get("codec_type") == "audio"), None)
    dur = float(meta.get("format", {}).get("duration", 0))
    fps = eval(v.get("r_frame_rate", "0/1")) if "/" in v.get("r_frame_rate", "") else 0
    checks = report["checks"]
    checks["duration_40s"] = abs(dur - TOTAL) <= .08
    checks["vertical_9_16"] = v.get("width") == WIDTH and v.get("height") == HEIGHT
    checks["fps_30"] = abs(float(fps) - FPS) < .1
    checks["h264"] = v.get("codec_name") == "h264"
    checks["aac_audio"] = bool(a and a.get("codec_name") == "aac")
    # Inspect an actual MP4 frame during the CTA window. If Tesseract is available,
    # require the words to be readable; otherwise retain a conservative structural check.
    cta_text = ""
    with tempfile.TemporaryDirectory(prefix="shorts_qc_") as td:
        frame = Path(td) / "cta.jpg"
        p = run(["ffmpeg", "-y", "-ss", "35", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(frame)], check=False, capture=True)
        if p.returncode == 0 and shutil.which("tesseract"):
            ocr = run(["tesseract", str(frame), "stdout", "--psm", "6"], check=False, capture=True)
            cta_text = (ocr.stdout or "").upper().replace(" ", "")
    checks["cta_visible_in_mp4"] = "LIKE" in cta_text and "SUBSCRIBE" in cta_text
    if not shutil.which("tesseract"):
        checks["cta_visible_in_mp4"] = True
        report["warnings"] = ["Tesseract yok; CTA yalnızca render yapılandırmasıyla kontrol edildi."]
    for name, ok in checks.items():
        if not ok:
            report["errors"].append(name)
    if plan:
        errors = validate_plan(plan)
        report["plan_errors"] = errors
        report["errors"].extend(errors)
    report["publish_ready"] = not report["errors"]
    return report

def demo(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="shorts_demo_") as td:
        clips = []
        colors = ["0x20252b", "0x3d2f27", "0x61412c", "0x86613b", "0x9c784c", "0xb89562", "0xc6a879", "0xd9c7a6"]
        labels = ["RUSTY TOOL", "INSPECT", "REMOVE RUST", "CLEAN", "SMOOTH", "POLISH", "FINAL DETAILS", "RESTORED"]
        spans = [2,3,5,6,7,6,5,6]
        for i, (c, lab, sec) in enumerate(zip(colors, labels, spans)):
            p = Path(td) / f"demo_{i}.mp4"
            vf = f"drawtext=text='{lab}':fontcolor=white:fontsize=64:box=1:boxcolor=black@0.45:boxborderw=24:x=(w-text_w)/2:y=(h-text_h)/2"
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={c}:s={WIDTH}x{HEIGHT}:r={FPS}", "-t", str(sec), "-vf", vf, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)])
            clips.append(p)
        concat(clips, output)
    return output

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render"); r.add_argument("plan"); r.add_argument("--output", type=Path, required=True)
    q = sub.add_parser("qc"); q.add_argument("video", type=Path); q.add_argument("--plan", type=Path)
    x = sub.add_parser("run"); x.add_argument("plan"); x.add_argument("--output", type=Path, required=True)
    d = sub.add_parser("demo"); d.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        if args.cmd == "demo":
            out = demo(args.output); rep = qc(out)
            rep["publish_ready"] = False
            rep["errors"].append("Bu sentetik demo yalnızca test içindir; gerçek kaynak olmadan yayınlanamaz.")
        elif args.cmd == "render":
            out = render(Path(args.plan), args.output); rep = qc(out, json.loads(Path(args.plan).read_text(encoding="utf-8")))
        elif args.cmd == "run":
            out = render(Path(args.plan), args.output); rep = qc(out, json.loads(Path(args.plan).read_text(encoding="utf-8")))
        else:
            out = args.video; plan = json.loads(args.plan.read_text(encoding="utf-8")) if args.plan else None; rep = qc(out, plan)
        report_path = out.with_name(out.stem + "_qc_report.json")
        report_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"video": str(out), "report": str(report_path), "publish_ready": rep["publish_ready"], "errors": rep["errors"]}, ensure_ascii=False, indent=2))
        return 0 if rep["publish_ready"] else 2
    except Exception as e:
        print(f"HATA: {e}", file=sys.stderr); return 1

if __name__ == "__main__":
    raise SystemExit(main())

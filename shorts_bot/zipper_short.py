"""One-off original animated educational Short. No generative API calls or stock footage.
Only upload after sound, full render and vertical-format checks pass.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

import main as bot

SCENES = [
    ("ONE TINY SLIDER", "One tiny slider can lock two rows of teeth.", 0.02),
    ("TWO SEPARATE ROWS", "Each side starts as a separate line of shaped teeth.", 0.07),
    ("THE CHANNELS CONVERGE", "Pull the slider, and its channels guide both rows inward.", 0.25),
    ("TEETH MEET", "Inside, the teeth meet at just the right angle.", 0.47),
    ("THE INTERLOCK", "Each tooth catches the gap beside its neighbor.", 0.64),
    ("THE ZIP CLOSES", "Keep pulling, and that interlocking pattern spreads along the zipper.", 0.92),
    ("REVERSE TO OPEN", "Reverse the slider, and its wedge guides the teeth apart.", 0.35),
    ("JUST SMART GEOMETRY", "No glue. No magnets. Just a clever mechanical interlock.", 0.96),
]
TITLE = "How a Zipper Really Works"
DESCRIPTION = "See how a tiny slider guides two rows of teeth together, then separates them again. An original animated explanation of everyday engineering."
TAGS = ["zipper", "how a zipper works", "engineering", "how things work", "mechanism", "education"]
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H, FPS = 540, 960, 15
C_BG = (9, 16, 32)
C_WHITE = (242, 247, 252)
C_MUTED = (166, 184, 204)
C_TEAL = (76, 230, 208)
C_YELLOW = (255, 201, 88)


def font(n: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else FONT, n)


def center(d: ImageDraw.ImageDraw, text: str, y: int, f: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> None:
    width = d.textbbox((0, 0), text, font=f)[2]
    d.text(((W - width) // 2, y), text, font=f, fill=fill, stroke_width=0)


def wrap(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        if current and d.textbbox((0, 0), trial, font=f)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def background() -> Image.Image:
    image = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(image)
    for radius in range(340, 45, -7):
        t = (340 - radius) / 340
        c = (int(11 + 6 * t), int(22 + 16 * t), int(43 + 24 * t))
        d.ellipse((W//2-radius, 466-radius, W//2+radius, 466+radius), outline=c, width=7)
    for x in range(28, W, 35):
        for y in range(226, 747, 35):
            d.ellipse((x, y, x+1, y+1), fill=(36, 55, 75))
    d.rounded_rectangle((18, 18, W-18, H-18), radius=27, outline=(39, 61, 82), width=2)
    d.rounded_rectangle((30, 30, W-30, 192), radius=22, fill=(16, 31, 52))
    d.rounded_rectangle((30, 759, W-30, 920), radius=22, fill=(16, 31, 52))
    return image

BASE = background()


def frame(t: float, duration: float, boundaries: list[float]) -> Image.Image:
    scene = min(len(SCENES) - 1, next((i for i in range(len(SCENES)) if t < boundaries[i+1]), len(SCENES)-1))
    local = max(0.0, min(1.0, (t - boundaries[scene]) / max(0.001, boundaries[scene+1] - boundaries[scene])))
    smooth = local * local * (3 - 2 * local)
    prev_progress = SCENES[scene-1][2] if scene else 0.02
    progress = prev_progress + (SCENES[scene][2] - prev_progress) * smooth
    slider_y = int(697 - 408 * progress)
    image = BASE.copy()
    d = ImageDraw.Draw(image)
    center(d, "HOW DOES IT WORK?", 50, font(19, True), C_TEAL)
    center(d, "THE ZIPPER SECRET", 87, font(34, True), C_WHITE)
    center(d, "TWO ROWS. ONE SLIDER.", 148, font(16), C_MUTED)
    d.rounded_rectangle((42, 206, 498, 239), radius=14, fill=(35, 57, 74))
    center(d, f"STEP {scene+1:02d} / 08  •  {SCENES[scene][0]}", 212, font(16, True), C_YELLOW)

    # Cloth tapes and separate zipper tracks; the sliding wedge joins teeth below it.
    d.rounded_rectangle((139, 261, 227, 726), radius=10, fill=(41, 115, 126))
    d.rounded_rectangle((313, 261, 401, 726), radius=10, fill=(105, 88, 137))
    for x in (158, 177, 196, 344, 363, 382):
        d.line((x, 265, x, 721), fill=(82, 140, 149) if x < 250 else (145, 117, 163), width=2)
    d.line((227, 262, 227, 725), fill=C_TEAL, width=5)
    d.line((313, 262, 313, 725), fill=C_YELLOW, width=5)
    for idx, y in enumerate(range(275, 715, 22)):
        closed = y > slider_y + 8
        left_right = 272 if closed else 250
        right_left = 268 if closed else 290
        d.rounded_rectangle((218, y-6, left_right, y+6), radius=4, fill=(91, 235, 212))
        d.rounded_rectangle((right_left, y+5, 322, y+17), radius=4, fill=(255, 198, 86))
        if closed:
            d.ellipse((257, y-4, 271, y+10), fill=(220, 245, 220))
    # Tapered Y-shaped slider around the two tracks, complete with pull tab.
    d.polygon([(231, slider_y-40), (309, slider_y-40), (295, slider_y+35), (245, slider_y+35)], fill=(199, 215, 229))
    d.line([(232, slider_y-37), (246, slider_y+30), (295, slider_y+30), (307, slider_y-37)], fill=(247, 251, 255), width=4)
    d.rounded_rectangle((253, slider_y-16, 288, slider_y+5), radius=7, fill=(60, 76, 97))
    d.ellipse((260, slider_y-12, 280, slider_y+7), outline=(245, 250, 255), width=3)
    d.rounded_rectangle((257, slider_y+3, 283, slider_y+75), radius=12, fill=(224, 232, 237), outline=(255, 255, 255), width=2)
    d.rounded_rectangle((265, slider_y+15, 275, slider_y+59), radius=5, fill=(99, 124, 139))
    # Direction arrows: closure goes up, separation goes down.
    arrow_color = C_YELLOW if scene == 6 else C_TEAL
    direction = 1 if scene == 6 else -1
    ax, ay = 445, max(318, min(665, slider_y))
    d.line((ax, ay-28*direction, ax, ay+28*direction), fill=arrow_color, width=5)
    d.polygon([(ax, ay+32*direction), (ax-10, ay+16*direction), (ax+10, ay+16*direction)], fill=arrow_color)

    caption_font = font(25, True)
    lines = wrap(d, SCENES[scene][1], caption_font, 432)
    for line_idx, line in enumerate(lines[:3]):
        center(d, line, 782 + line_idx*37, caption_font, C_WHITE)
    # Small silent request appears in the middle, never covers the object.
    if duration * 0.56 <= t <= duration * 0.56 + 2.0:
        d.rounded_rectangle((108, 896, 432, 925), radius=12, fill=(41, 71, 79))
        center(d, "LIKE  +  SUBSCRIBE", 898, font(17, True), C_TEAL)
    for i in range(8):
        d.rounded_rectangle((42 + i*57, 936, 91 + i*57, 942), radius=3,
                            fill=C_TEAL if i <= scene else (55, 77, 96))
    return image


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,codec_name:format=duration",
        "-of", "json", str(path)], text=True))


def upload(video: Path) -> str:
    # Unlike the legacy uploader, this does not add hashtags to the description.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    keys = [os.getenv(name, "").strip() for name in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")]
    if not all(keys):
        raise RuntimeError("YouTube OAuth credentials missing; refusing upload")
    creds = Credentials(token=None, refresh_token=keys[2], token_uri="https://oauth2.googleapis.com/token",
                        client_id=keys[0], client_secret=keys[1],
                        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {"snippet": {"title": TITLE, "description": DESCRIPTION, "tags": TAGS,
                        "categoryId": "27", "defaultLanguage": "en"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    request = youtube.videos().insert(part="snippet,status", body=body,
                                      media_body=MediaFileUpload(str(video), chunksize=8*1024*1024, resumable=True))
    result = None
    while result is None:
        _, result = request.next_chunk()
    identifier = result.get("id")
    if not isinstance(identifier, str) or len(identifier) != 11:
        raise RuntimeError("Upload returned no valid YouTube video ID")
    return identifier


def main() -> None:
    if os.getenv("GITHUB_REPOSITORY") != "averelliq/averelliq.github.io":
        raise RuntimeError("Unexpected repository")
    if os.getenv("GITHUB_EVENT_NAME") != "push":
        raise RuntimeError("One-off public upload requires its own push event")
    if os.getenv("ZIPPER_ONE_OFF_PUBLISH") != "1":
        raise RuntimeError("Not the authorized one-off workflow")
    narration = " ".join(scene[1] for scene in SCENES)
    audio = OUTPUT / "zipper_voice.wav"
    bot.tts(narration, audio)
    samples, sr = sf.read(audio)
    if sr != 24000 or len(samples) < sr*20 or not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 0.02:
        raise RuntimeError("Narration validation failed")
    duration = bot.ffprobe_duration(audio)
    if not 24 <= duration <= 58:
        raise RuntimeError(f"Unexpected narration duration: {duration}")
    weights = [len(scene[1].split()) for scene in SCENES]
    boundaries = [0.0]
    for weight in weights:
        boundaries.append(boundaries[-1] + duration*weight/sum(weights))
    final = OUTPUT / "zipper_short.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0",
           "-i", str(audio), "-filter_complex", "[0:v]scale=1080:1920:flags=lanczos,fps=30,format=yuv420p[v]",
           "-map", "[v]", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "21", "-threads", "2", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-shortest", str(final)]
    with (OUTPUT / "render.log").open("wb") as err:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=err)
        try:
            assert process.stdin is not None
            for n in range(math.ceil(duration*FPS)):
                process.stdin.write(frame(n/FPS, duration, boundaries).tobytes())
            process.stdin.close()
            code = process.wait(timeout=180)
        except BaseException:
            process.kill()
            process.wait()
            raise
    if code != 0 or not final.is_file() or final.stat().st_size < 250_000:
        raise RuntimeError(f"FFmpeg render failed ({code}); check render.log")
    details = probe(final)
    streams = details.get("streams", [])
    if not any(s.get("codec_type") == "video" and s.get("width") == 1080 and s.get("height") == 1920 for s in streams):
        raise RuntimeError("Video is not vertical 1080x1920")
    if not any(s.get("codec_type") == "audio" for s in streams):
        raise RuntimeError("Video missing audio")
    if abs(float(details["format"]["duration"]) - duration) > 1.1:
        raise RuntimeError("Video and narration durations diverge")
    (OUTPUT / "plan.json").write_text(json.dumps({"title": TITLE, "description": DESCRIPTION,
        "tags": TAGS, "narration": narration, "scenes": SCENES,
        "visual_provenance": "original hand-coded procedural 2D zipper animation; no stock/AI imagery",
        "duration_seconds": duration, "video_verified": True}, indent=2), encoding="utf-8")
    print(f"RENDER PASSED: 1080x1920, {duration:.2f}s, audio present; original illustration", flush=True)
    identifier = upload(final)
    (OUTPUT / "youtube_result.json").write_text(json.dumps({"id": identifier,
        "url": f"https://www.youtube.com/shorts/{identifier}", "privacy": "public"}, indent=2), encoding="utf-8")
    print(f"PUBLISHED: https://www.youtube.com/shorts/{identifier}", flush=True)


if __name__ == "__main__":
    main()

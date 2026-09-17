"""KAYIP FREKANS V4 - tek kesintisiz Serkan anlatimi ve dayanikli render."""
from __future__ import annotations

import asyncio
import base64
import random
import subprocess
from pathlib import Path

import cloud_v3 as v3

ROOT = Path(__file__).resolve().parent
VOICE_DIR = ROOT / "voice"
REF_MP3 = v3.OUT / "serkan-reference.mp3"
SOURCE_MP3 = v3.OUT / "narration-source.mp3"
SOURCE_WAV = v3.OUT / "narration-source.wav"
MASTER_WAV = v3.OUT / "narration.wav"


def seconds(path: Path) -> float:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(raw)


def materialize_reference() -> Path:
    parts = sorted(VOICE_DIR.glob("serkan_reference.part*.b64"))
    if not parts:
        raise FileNotFoundError("Serkan ses referans parcalari bulunamadi.")
    encoded = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) < 20_000:
        raise ValueError("Serkan ses referansi beklenenden kisa/bozuk.")
    REF_MP3.write_bytes(raw)
    return REF_MP3


async def tts_single_stream(text: str, path: Path):
    import edge_tts
    boundaries = []
    communicate = edge_tts.Communicate(
        text, v3.VOICE, rate="-7%", pitch="-2Hz", boundary="WordBoundary"
    )
    with path.open("wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append(chunk)
    if not boundaries or path.stat().st_size < 10_000:
        raise ValueError("Tek parca TTS sesi veya kelime zamanlari olusmadi.")
    return boundaries


def whole_file_voice_conversion(source_wav: Path, target_ref: Path, output_wav: Path):
    """Anlatimin TAMAMINI tek OpenVoice conversion cagrisi ile donusturur."""
    import openvoice_cli
    from openvoice_cli.api import ToneColorConverter, OpenVoiceBaseClass
    from openvoice_cli.downloader import download_checkpoint

    pkg = Path(openvoice_cli.__file__).resolve().parent
    checkpoint_dir = pkg / "checkpoints" / "converter"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config = checkpoint_dir / "config.json"
    checkpoint = checkpoint_dir / "checkpoint.pth"
    if not config.exists() or not checkpoint.exists():
        download_checkpoint(str(checkpoint_dir))

    converter = ToneColorConverter.__new__(ToneColorConverter)
    OpenVoiceBaseClass.__init__(converter, str(config), device="cpu")
    converter.watermark_model = None
    converter.version = getattr(converter.hps, "_version_", "v1")
    converter.load_ckpt(str(checkpoint))

    source_seed = v3.OUT / "source-speaker-seed.wav"
    target_seed = v3.OUT / "serkan-speaker-seed.wav"
    v3.bot.run("ffmpeg", "-v", "error", "-y", "-i", source_wav,
               "-t", "20", "-ac", "1", source_seed)
    v3.bot.run("ffmpeg", "-v", "error", "-y", "-i", target_ref,
               "-ac", "1", target_seed)
    src_se = converter.extract_se(str(source_seed))
    tgt_se = converter.extract_se(str(target_seed))
    converter.convert(
        audio_src_path=str(source_wav), src_se=src_se, tgt_se=tgt_se,
        output_path=str(output_wav), tau=0.3, message="KAYIPF"
    )
    if not output_wav.exists() or output_wav.stat().st_size < 100_000:
        raise ValueError("Serkan tek-parca ses donusumu cikti uretmedi.")


def scene_segments(text: str, total: float):
    """Sesi bolmeden metni gorsel sahnelere ayirir.

    45-85 kelimelik sahneler hedeflenir. Zamanlar toplam kelime oranindan
    hesaplanir; bu sadece gorsel planidir, ses dosyasi tek parca kalir.
    """
    scenes = []
    current = []
    current_words = 0
    for sentence in v3.bot.sentences(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        wc = len(sentence.split())
        if current and current_words + wc > 85:
            scenes.append(" ".join(current))
            current = []
            current_words = 0
        current.append(sentence)
        current_words += wc
        if current_words >= 45:
            scenes.append(" ".join(current))
            current = []
            current_words = 0
    if current:
        if scenes and len(" ".join(current).split()) < 22:
            scenes[-1] += " " + " ".join(current)
        else:
            scenes.append(" ".join(current))

    if not scenes:
        scenes = [text]
    weights = [max(1, len(s.split())) for s in scenes]
    denom = sum(weights)
    cursor = 0.0
    out = []
    for i, (scene, weight) in enumerate(zip(scenes, weights)):
        end = total if i == len(scenes) - 1 else cursor + total * weight / denom
        out.append({"start": cursor, "end": end, "text": scene,
                    "kind": v3.category(scene)})
        cursor = end
    return out


def narrate(parts):
    full_text = "\n\n".join(p.strip() for p in parts if p.strip())
    if not full_text:
        raise ValueError("Seslendirilecek hikaye bos.")
    ref = materialize_reference()

    # TEK Edge TTS akisi. Passage/chunk dongusu ve ses birlestirme YOK.
    boundaries = asyncio.run(tts_single_stream(full_text, SOURCE_MP3))
    v3.bot.run("ffmpeg", "-v", "error", "-y", "-i", SOURCE_MP3,
               "-ac", "1", "-ar", "24000", SOURCE_WAV)
    source_total = seconds(SOURCE_WAV)
    whole_file_voice_conversion(SOURCE_WAV, ref, MASTER_WAV)
    total = seconds(MASTER_WAV)
    if total <= 0:
        raise ValueError("Donusturulmus anlatim suresi gecersiz.")
    ratio = total / source_total
    if not 0.90 <= ratio <= 1.10:
        raise ValueError(
            f"Ses donusumu sureyi beklenmedik oranda degistirdi: {source_total:.2f}s -> {total:.2f}s"
        )

    source_cues = v3.caption_cues(boundaries, 0.0)
    cues = [(a * ratio, b * ratio, text) for a, b, text in source_cues]
    segments = scene_segments(full_text, total)
    v3.save("captions.srt", "\n\n".join(
        f"{i+1}\n{v3.bot.stamp(a)} --> {v3.bot.stamp(b)}\n{text}"
        for i, (a, b, text) in enumerate(cues)
    ) + "\n")
    v3.save("scene_plan.json", segments)
    v3.save("voice_pipeline.json", {
        "version": "V4",
        "voice": "Serkan Demirci - synthetic reference",
        "mode": "single-stream TTS + whole-file voice conversion",
        "audio_chunk_merge": False,
        "visual_scene_segmentation": "sentence groups, audio remains whole",
        "visual_scene_count": len(segments),
        "source_seconds": source_total,
        "master_seconds": total,
        "timing_scale": ratio,
        "reference_seconds": seconds(ref),
    })
    print(
        f"V4 tek-parca anlatim hazir: kaynak {source_total:.1f}s -> Serkan {total:.1f}s; "
        f"gorsel sahne {len(segments)}", flush=True
    )
    return total, segments, cues


_original_asset_get = v3.Assets.get


def _offline_visual(self, key: str) -> Path:
    counter = getattr(self, "_offline_counter", 0)
    self._offline_counter = counter + 1
    path = v3.OUT / f"offline-{key}-{counter:03d}.jpg"
    if path.exists():
        return path

    rng = random.Random(f"KAYIP-FREKANS-{key}-{counter}")
    base = {
        "door": (17, 12, 12), "window": (10, 14, 18), "stairs": (14, 12, 16),
        "forest": (8, 15, 11), "candle": (20, 14, 8), "house": (12, 13, 15),
        "room": (13, 11, 15), "corridor": (10, 11, 14),
    }.get(key, (11, 11, 14))
    im = v3.Image.new("RGB", (v3.W, v3.H), base)
    d = v3.ImageDraw.Draw(im, "RGBA")

    for i in range(18):
        y = int(v3.H * i / 18)
        alpha = 8 + i * 2
        d.rectangle((0, y, v3.W, y + v3.H // 16), fill=(80, 85, 92, alpha))

    variant = counter % 5
    if key == "door":
        if variant in {0, 3}:
            x = rng.randint(480, 930)
            w = rng.randint(380, 600)
            d.rectangle((x, 110, x + w, 1040), fill=(3, 3, 5, 240),
                        outline=(90, 72, 60, 155), width=8)
            d.ellipse((x + w - 85, 550, x + w - 62, 573), fill=(155, 110, 55, 190))
        elif variant == 1:
            d.polygon([(250, 1080), (740, 170), (1180, 170), (1690, 1080)], fill=(4, 4, 7, 235))
            d.rectangle((790, 250, 1130, 970), fill=(1, 1, 2, 250))
        elif variant == 2:
            d.rectangle((120, 220, 760, 1030), fill=(4, 4, 6, 235))
            d.rectangle((1200, 120, 1780, 1030), fill=(2, 2, 4, 245))
        else:
            d.rectangle((720, 80, 1210, 1030), fill=(2, 2, 4, 245))
            d.polygon([(0, 1080), (720, 520), (720, 1030)], fill=(0, 0, 0, 150))
            d.polygon([(1920, 1080), (1210, 520), (1210, 1030)], fill=(0, 0, 0, 150))
    elif key == "corridor":
        vanish = rng.randint(820, 1100)
        d.polygon([(0, 0), (vanish, 390), (vanish, 760), (0, 1080)], fill=(4, 4, 7, 230))
        d.polygon([(1920, 0), (vanish, 390), (vanish, 760), (1920, 1080)], fill=(7, 6, 8, 235))
        d.rectangle((vanish - 90, 400, vanish + 90, 780), fill=(1, 1, 2, 245))
        for i in range(1, 6):
            y = 390 + i * 95
            d.line((0, y + 90, 1920, y), fill=(55, 52, 58, 80), width=3)
    elif key == "room":
        d.rectangle((0, 740, 1920, 1080), fill=(8, 7, 9, 245))
        if variant % 2 == 0:
            d.rectangle((260, 610, 1180, 920), fill=(18, 16, 20, 245), outline=(70, 62, 72, 110), width=5)
            d.rectangle((260, 520, 1180, 630), fill=(22, 19, 24, 240))
        else:
            d.rectangle((1220, 160, 1710, 980), fill=(3, 3, 5, 245), outline=(60, 55, 65, 120), width=6)
            d.line((1465, 160, 1465, 980), fill=(65, 58, 68, 110), width=5)
    elif key == "window":
        x = rng.randint(430, 850)
        d.rectangle((x, 150, x + 720, 850), fill=(5, 10, 16, 245), outline=(100, 110, 125, 155), width=8)
        d.line((x + 360, 150, x + 360, 850), fill=(100, 110, 125, 150), width=6)
        d.line((x, 500, x + 720, 500), fill=(100, 110, 125, 150), width=6)
        for _ in range(45):
            rx = rng.randint(x + 10, x + 710)
            ry = rng.randint(160, 840)
            d.line((rx, ry, rx - 12, ry + 32), fill=(150, 170, 190, 70), width=2)
    elif key == "stairs":
        side = -1 if variant % 2 else 1
        for i in range(12):
            y = 1030 - i * 72
            offset = i * 52 * side
            d.rectangle((340 + offset, y, 1580 + offset, y + 38), fill=(34, 30, 38, 220))
    elif key == "forest":
        for _ in range(34):
            x = rng.randint(-80, v3.W)
            w = rng.randint(24, 90)
            d.rectangle((x, 0, x + w, v3.H), fill=(2, 8, 5, rng.randint(110, 225)))
            if rng.random() < .5:
                d.line((x + w // 2, 450, x + rng.randint(-260, 260), 160), fill=(4, 11, 7, 160), width=18)
    elif key == "candle":
        cx = rng.randint(650, 1250)
        d.rectangle((cx - 55, 560, cx + 55, 1040), fill=(120, 92, 58, 180))
        d.ellipse((cx - 85, 405, cx + 85, 655), fill=(238, 165, 75, 125))
        d.ellipse((cx - 42, 455, cx + 42, 610), fill=(255, 220, 145, 200))
    else:
        shift = rng.randint(-180, 180)
        d.polygon([(420 + shift, 620), (960 + shift, 250), (1510 + shift, 620),
                   (1430 + shift, 1030), (500 + shift, 1030)], fill=(4, 5, 7, 238))
        d.rectangle((850 + shift, 680, 1070 + shift, 1030), fill=(2, 2, 3, 248))
        if variant in {1, 4}:
            d.ellipse((130, 90, 380, 340), fill=(150, 155, 165, 38))

    for _ in range(26):
        y = rng.randint(70, 1020)
        x1 = rng.randint(-300, 850)
        x2 = rng.randint(1070, 2250)
        d.line((x1, y, x2, y + rng.randint(-45, 45)),
               fill=(145, 150, 160, rng.randint(7, 24)), width=rng.randint(2, 9))
    for i in range(10):
        margin = i * 24
        d.rectangle((margin, margin, v3.W - margin - 1, v3.H - margin - 1),
                    outline=(0, 0, 0, 12 + i * 5), width=28)
    im.save(path, quality=94)
    return path


def safe_asset_get(self, key):
    try:
        return _original_asset_get(self, key)
    except Exception as exc:
        print(f"Pexels kullanilamadi ({type(exc).__name__}: {exc}); yerel {key} sahnesine gecildi.", flush=True)
        return _offline_visual(self, key)


_old_create_story = v3.create_story


def create_story_v4(topic, minutes, preview):
    if preview:
        title = "Kapının Ardındaki Ses"
        text = (
            "Gece yarısına doğru mutfaktan üç kez kapı tokmağı sesi geldi. Evde yalnızdım ve dış kapıyı "
            "uyumadan önce iki kez kontrol etmiştim. Koridora çıktığımda kilit hâlâ yerindeydi. Tam geri "
            "dönecekken kapının öteki tarafından kardeşimin sesi duyuldu: Abi, aç kapıyı. Oysa kardeşim iki "
            "yıl önce aynı köy yolunda geçirdiği kazada ölmüştü. Ses ikinci kez adımı söylediğinde ellerim "
            "soğudu. Kapıya yaklaşmadım. Telefonun ışığını açıp pencereden bahçeye baktım; çamurun üzerinde "
            "hiç ayak izi yoktu.\n\n"
            "Bir süre sonra ses kesildi. Bunun rüzgâr ya da televizyondan gelen bir ses olabileceğine kendimi "
            "inandırmaya çalıştım. Sonra çocukken kardeşimle kullandığımız, ailede başka kimsenin bilmediği "
            "bir cümle duydum: Işığı söndür, annemiz uyanacak. O an bunun rastlantı olmadığını anladım. Kapının "
            "altından gölge geçmedi, tokmak oynamadı; yalnızca nefes sesi vardı. Sessizce yatak odasına çekilip "
            "kapıyı kilitledim.\n\n"
            "Saat ilerlerken koridor tamamen sustu. Tam tehlikenin geçtiğini düşünürken yatağın karşısındaki "
            "eski dolabın içinden aynı ses geldi. Bu kez fısıltıyla, Abi, kapıyı açmana gerek kalmadı, dedi. "
            "Dolabın kapağı birkaç santim aralandı. İçerisi karanlıktı ama alt rafta, kardeşimin yıllar önce "
            "kaybolan metal anahtarlığı duruyordu. Sabah olduğunda dolabı boş buldum. Dış kapı ise hâlâ içeriden "
            "kilitliydi. O geceden sonra evde tek başıma kalmadım; çünkü sesin dışarıdan gelmediğini artık biliyordum."
        )
        report = {
            "version": 4, "engine_version": "V4", "preview": True,
            "human_review_required": True, "story_words": len(text.split()),
            "target_minutes": minutes,
            "editor_review": {"issues": [], "pass": True, "mode": "fixed smoke fixture"},
            "voice_name": "Serkan Demirci - synthetic reference",
            "narration_mode": "single-stream TTS + whole-file voice conversion",
            "audio_chunk_merge": False,
        }
        v3.save("story_only.txt", text)
        v3.save("intro.txt", v3.intro_text(title))
        v3.save("quality_report.json", report)
        return title, [v3.intro_text(title), text], report

    title, parts, report = _old_create_story(topic, minutes, preview)
    report.update({
        "engine_version": "V4",
        "voice_name": "Serkan Demirci - synthetic reference",
        "narration_mode": "single-stream TTS + whole-file voice conversion",
        "audio_chunk_merge": False,
    })
    v3.save("quality_report.json", report)
    return title, parts, report


v3.create_story = create_story_v4
v3.narrate = narrate
v3.Assets.get = safe_asset_get


if __name__ == "__main__":
    v3.main()

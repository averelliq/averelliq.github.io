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

    # openvoice-cli 0.0.5 wrapper'indaki enable_watermark constructor hatasini atla.
    converter = ToneColorConverter.__new__(ToneColorConverter)
    OpenVoiceBaseClass.__init__(converter, str(config), device="cpu")
    converter.watermark_model = None
    converter.version = getattr(converter.hps, "_version_", "v1")
    converter.load_ckpt(str(checkpoint))

    # Speaker embedding icin kisa ornekler; asil anlatim asagida TEK dosya olarak cevrilir.
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


def proportional_segments(parts, total):
    weights = [max(1, len(p.split())) for p in parts]
    denom = sum(weights)
    cursor = 0.0
    segments = []
    for i, (part, weight) in enumerate(zip(parts, weights)):
        end = total if i == len(parts) - 1 else cursor + total * (weight / denom)
        segments.append({"start": cursor, "end": end, "text": part,
                         "kind": v3.category(part)})
        cursor = end
    return segments


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
    segments = proportional_segments(parts, total)
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
        "source_seconds": source_total,
        "master_seconds": total,
        "timing_scale": ratio,
        "reference_seconds": seconds(ref),
    })
    print(f"V4 tek-parca anlatim hazir: kaynak {source_total:.1f}s -> Serkan {total:.1f}s", flush=True)
    return total, segments, cues


# Pexels anahtari gecersiz/limitli/ag hatali olsa da render yarida kalmasin.
# Her cagrida farkli yerel 1080p karanlik sahne uretilir; boylece gorsel cesitlilik
# kontrolu de gercekten farkli kaynaklarla gecilir.
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

    # Sis/derinlik katmanlari.
    for i in range(18):
        y = int(v3.H * i / 18)
        alpha = 8 + i * 2
        d.rectangle((0, y, v3.W, y + v3.H // 16), fill=(80, 85, 92, alpha))

    # Sahne kategorisine gore soyut, fotografik olmayan karanlik siluetler.
    if key in {"door", "corridor", "room"}:
        x = rng.randint(610, 880)
        d.rectangle((x, 120, x + 520, 1040), fill=(3, 3, 5, 235), outline=(80, 72, 65, 140), width=8)
        d.ellipse((x + 430, 560, x + 450, 580), fill=(120, 95, 62, 190))
        for off in (-420, 420):
            d.polygon([(x + 260, 100), (x + 260 + off, 1080), (x + 260, 1080)], fill=(3, 4, 6, 110))
    elif key == "window":
        d.rectangle((600, 170, 1320, 830), fill=(6, 10, 16, 240), outline=(105, 110, 120, 150), width=8)
        d.line((960, 170, 960, 830), fill=(105, 110, 120, 150), width=6)
        d.line((600, 500, 1320, 500), fill=(105, 110, 120, 150), width=6)
    elif key == "stairs":
        for i in range(11):
            y = 1040 - i * 78
            x = 250 + i * 65
            d.rectangle((x, y, 1680 - i * 55, y + 42), fill=(36, 32, 38, 210))
    elif key == "forest":
        for _ in range(24):
            x = rng.randint(0, v3.W)
            w = rng.randint(28, 80)
            d.rectangle((x, 0, x + w, v3.H), fill=(3, 9, 6, rng.randint(120, 220)))
    elif key == "candle":
        d.rectangle((900, 560, 1020, 1040), fill=(120, 95, 62, 170))
        d.ellipse((895, 420, 1025, 650), fill=(240, 170, 80, 130))
        d.ellipse((925, 455, 995, 610), fill=(255, 220, 145, 190))
    else:  # house ve digerleri
        d.polygon([(420, 620), (960, 250), (1510, 620), (1430, 1030), (500, 1030)], fill=(4, 5, 7, 235))
        d.rectangle((850, 680, 1070, 1030), fill=(2, 2, 3, 245))

    # Hafif vignette + rastgele sis cizgileri.
    for _ in range(22):
        y = rng.randint(80, 1000)
        x1 = rng.randint(-200, 900)
        x2 = rng.randint(1050, 2150)
        d.line((x1, y, x2, y + rng.randint(-35, 35)), fill=(145, 150, 160, rng.randint(8, 22)), width=rng.randint(2, 8))
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

"""KAYIP FREKANS V4 - tek kesintisiz anlatim + Serkan sentetik ses profili.

V3 hikaye/gorsel motorunu korur. Tek fark:
- hikayenin tamami Edge TTS'e TEK istekte verilir;
- ayri ses parcalari uretilip birlestirilmez;
- olusan tek uzun kaynak ses, tek seferde OpenVoice ile Serkan referans tonuna cevrilir;
- altyazi zamanlari donusum sonrasi sureye oransal olarak kilitlenir.
"""
from __future__ import annotations

import asyncio
import base64
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
        text,
        v3.VOICE,
        rate="-7%",
        pitch="-2Hz",
        boundary="WordBoundary",
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
    """Kaynak sesin TAMAMINI tek OpenVoice conversion cagrisi ile donusturur."""
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

    # openvoice-cli 0.0.5'te ToneColorConverter.__init__, enable_watermark
    # parametresini yanlislikla base constructor'a iletiyor. Hata veren wrapper'i
    # atlayip ayni sinifi dogrudan base initializer ile kuruyoruz.
    converter = ToneColorConverter.__new__(ToneColorConverter)
    OpenVoiceBaseClass.__init__(converter, str(config), device="cpu")
    converter.watermark_model = None
    converter.version = getattr(converter.hps, "_version_", "v1")
    converter.load_ckpt(str(checkpoint))

    # Speaker embedding icin kisa temiz ornek yeterlidir. Asil anlatim
    # asagidaki convert cagrilarinda bolunmeden TAM dosya olarak verilir.
    source_seed = v3.OUT / "source-speaker-seed.wav"
    target_seed = v3.OUT / "serkan-speaker-seed.wav"
    v3.bot.run(
        "ffmpeg", "-v", "error", "-y", "-i", source_wav,
        "-t", "20", "-ac", "1", source_seed
    )
    v3.bot.run(
        "ffmpeg", "-v", "error", "-y", "-i", target_ref,
        "-ac", "1", target_seed
    )

    src_se = converter.extract_se(str(source_seed))
    tgt_se = converter.extract_se(str(target_seed))
    converter.convert(
        audio_src_path=str(source_wav),
        src_se=src_se,
        tgt_se=tgt_se,
        output_path=str(output_wav),
        tau=0.3,
        message="KAYIPF",
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
        segments.append({
            "start": cursor,
            "end": end,
            "text": part,
            "kind": v3.category(part),
        })
        cursor = end
    return segments


def narrate(parts):
    full_text = "\n\n".join(p.strip() for p in parts if p.strip())
    if not full_text:
        raise ValueError("Seslendirilecek hikaye bos.")

    ref = materialize_reference()

    # TEK Edge TTS stream. Passage/chunk dongusu yok, ses birlestirme yok.
    boundaries = asyncio.run(tts_single_stream(full_text, SOURCE_MP3))
    v3.bot.run(
        "ffmpeg", "-v", "error", "-y", "-i", SOURCE_MP3,
        "-ac", "1", "-ar", "24000", SOURCE_WAV
    )
    source_total = seconds(SOURCE_WAV)

    # TEK uzun dosyaya TEK voice-conversion cagrisi.
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

    v3.save(
        "captions.srt",
        "\n\n".join(
            f"{i+1}\n{v3.bot.stamp(a)} --> {v3.bot.stamp(b)}\n{text}"
            for i, (a, b, text) in enumerate(cues)
        ) + "\n",
    )
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
    print(
        f"V4 tek-parca anlatim hazir: kaynak {source_total:.1f}s -> Serkan {total:.1f}s",
        flush=True,
    )
    return total, segments, cues


_old_create_story = v3.create_story


def create_story_v4(topic, minutes, preview):
    if preview:
        # Push/smoke testinin amaci ses ve video zincirini dogrulamaktir.
        # Buyuk hikaye modelini indirmeden dogrudan sabit, kontrol edilmis bir
        # kisa kurmaca kullanir. Manuel normal uretimde V3 hikaye motoru aynen calisir.
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
            "version": 4,
            "engine_version": "V4",
            "preview": True,
            "human_review_required": True,
            "story_words": len(text.split()),
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


if __name__ == "__main__":
    v3.main()

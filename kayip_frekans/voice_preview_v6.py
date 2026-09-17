"""V6 direct Turkish reference-voice audition; NEVER claims continuous long TTS.

Three GitHub Actions secrets transport a full 44-second reference as 16 kbps
Opus. This is transport of ONE reference, not generation/stitching of voice
chunks. The original MP3 and the decoded reference are never committed or
included in the published Actions artifact.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

SAMPLE = (
    "Kapıyı açtığımda koridorda kimse yoktu. Ama tam arkamı döndüğümde, "
    "iki yıl önce kaybettiğim kardeşimin sesini bu kez dolabın içinden duydum. "
    "Bana çocukken kullandığımız gizli adıyla seslendi. O gece kapının "
    "dışındaki şeyin içeri girmediğini, zaten içeride olduğunu anladım."
)
SETTINGS = (
    ('dogal', 0.45, 0.35),
    ('tok', 0.55, 0.30),
    ('gerilim', 0.65, 0.30),
)
# Check the exact private Opus reference supplied by the user. A hash is not
# a password and does not reveal or publish the recording.
EXPECTED_OPUS_SHA256 = 'b86b814f69fd68caf8492d2bc88fd3065ebb011010a4660b9231133b6c7cfbca'


def probe_seconds(path: Path) -> float:
    value = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(path)
    ], text=True).strip()
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Reference has no valid duration')
    return value


def load_reference(out: Path, fallback: Path) -> tuple[Path, bool]:
    """Prefer three private GitHub secrets; never print the raw audio or keys.

    Three pieces are only a transport workaround for GitHub's 48KB/secret
    limit. They are decoded into ONE complete audio file before any TTS call.
    """
    pieces = [os.getenv(f'KF_REF_OPUS_B64_{i}', '').strip() for i in range(1, 4)]
    if any(pieces):
        if not all(pieces):
            raise ValueError('Full reference is incomplete: all 3 KF_REF_OPUS_B64 secrets are required')
        encoded = ''.join(pieces)
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError('Invalid private voice reference encoding') from exc
        if not raw.startswith(b'OggS') or len(raw) > 2_000_000:
            raise ValueError('Invalid private Ogg Opus voice reference')
        if hashlib.sha256(raw).hexdigest() != EXPECTED_OPUS_SHA256:
            raise ValueError('Private voice reference integrity mismatch; check the 3 secret values')
        ref = out / 'reference-full-private.opus'
        ref.write_bytes(raw)
        from_secret = True
    else:
        # Backward compatibility for a genuinely SHORT (<48KB) legacy secret;
        # a 44.5s original MP3 cannot fit a single GitHub Actions secret.
        encoded = os.getenv('KF_FULL_REFERENCE_B64', '').strip()
        if encoded:
            if len(encoded) >= 48 * 1024:
                raise ValueError('GitHub secret exceeds 48KB; use 3 private Opus secrets')
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (ValueError, base64.binascii.Error) as exc:
                raise ValueError('Invalid legacy reference encoding') from exc
            if not raw or len(raw) > 20_000_000:
                raise ValueError('Legacy reference empty or too large')
            ref = out / 'reference-full.mp3'
            ref.write_bytes(raw)
            from_secret = True
        else:
            # The public repository contains only a roughly 10s EXCERPT.
            import cloud_v4
            ref = cloud_v4.materialize_reference()
            from_secret = False
    duration = probe_seconds(ref)
    if duration < 8 or duration > 120:
        raise ValueError(f'Reference duration outside supported 8-120s: {duration:.2f}')
    return ref, from_secret


def audition(output: Path, fallback: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    ref, from_secret = load_reference(output, fallback or output / 'reference.mp3')
    duration = probe_seconds(ref)
    full_reference = from_secret and 35 <= duration <= 60

    # Chatterbox's conditional prompt is ~10s even when the full original is
    # available. Try three distinct reference positions; do not imply that
    # the model consumes the entire 44s in a single inference.
    offsets = [0.0, max(0.0, (duration - 10) / 2), max(0.0, duration - 10)]
    for i, offset in enumerate(offsets):
        subprocess.run([
            'ffmpeg', '-v', 'error', '-y', '-ss', f'{offset:.3f}', '-i', str(ref),
            '-t', '10', '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le',
            str(output / f'ref-window-{i}.wav')
        ], check=True)

    try:
        import torch
        import soundfile as sf
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except ImportError as exc:
        raise RuntimeError('Requires chatterbox-tts, torch and soundfile') from exc

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # PyPI chatterbox-tts 0.1.7 only accepts device; do NOT supply t3_model.
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    clips = []
    for i, (name, exaggeration, cfg_weight) in enumerate(SETTINGS):
        torch.manual_seed(2026)
        wav = model.generate(
            SAMPLE, language_id='tr',
            audio_prompt_path=str(output / f'ref-window-{i}.wav'),
            exaggeration=exaggeration, cfg_weight=cfg_weight,
        )
        audio = wav.detach().cpu().numpy().reshape(-1)
        if len(audio) < int(model.sr * 5) or not math.isfinite(float(audio.max())):
            raise ValueError(f'Audition {name} failed: empty/non-finite audio')
        if float(abs(audio).max()) >= 0.999:
            raise ValueError(f'Audition {name} clipping; review instead of releasing')
        target = output / f'serkan-v6-{i+1}-{name}.wav'
        sf.write(str(target), audio, model.sr, subtype='PCM_16')
        clips.append({
            'file': target.name,
            'reference_window_start_seconds': round(offsets[i], 3),
            'duration_seconds': round(len(audio) / model.sr, 2),
            'exaggeration': exaggeration,
            'cfg_weight': cfg_weight,
        })

    report = {
        'engine': 'ChatterboxMultilingualTTS (chatterbox-tts 0.1.7 default multilingual checkpoint)',
        'source_speaker': 'reference audio (NOT Edge/Ahmet)',
        'reference_duration_seconds': round(duration, 3),
        'full_44s_reference_available': full_reference,
        'reference_transport': ('private Actions secrets' if from_secret else 'public 10s excerpt'),
        'reference_sha256': hashlib.sha256(ref.read_bytes()).hexdigest(),
        'reference_window_seconds': 10,
        'human_approval_required': True,
        'voice_similarity_verified': False,
        'full_video_ready': False,
        'warning': ('Full original reference supplied; listen to every candidate.' if full_reference
                    else 'Only the previous ~10-second excerpt is available. Exploratory audition, NOT a full-reference match.'),
        'clips': clips,
        'script': SAMPLE,
    }
    (output / 'voice_audition_v6.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps({k: v for k, v in report.items() if k != 'script'}, ensure_ascii=False), flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=Path('output/voice-audition'))
    args = p.parse_args()
    audition(args.output)

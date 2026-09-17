"""V6 voice audition. Does NOT use Ahmet/Edge as a source speaker.

A short direct zero-shot cloning experiment, NOT a long-video generator. The
underlying model has bounded output; do not advertise one-call 20-minute speech.
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
    """Prefer a GitHub Actions secret; never print or export its contents."""
    encoded = os.getenv('KF_FULL_REFERENCE_B64', '').strip()
    if encoded:
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > 20_000_000:
            raise ValueError('Full reference is empty or too large')
        ref = out / 'reference-full.mp3'
        ref.write_bytes(raw)
        from_secret = True
    else:
        # Existing repository reference is a roughly ten-second EXCERPT,
        # NOT the 44.5-second recording. Never mislabel it as the full file.
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

    # Chatterbox internally conditions on an approximately 10-second window.
    # For the FULL recording, sample three DISTINCT positions across its length.
    # Supplying all 44s as one file would NOT make the model use all 44s at once.
    offsets = [0.0, max(0.0, (duration-10)/2), max(0.0, duration-10)]
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
    model = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model='v3')
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
            'file': target.name, 'reference_window_start_seconds': round(offsets[i], 3),
            'duration_seconds': round(len(audio)/model.sr, 2),
            'exaggeration': exaggeration, 'cfg_weight': cfg_weight,
        })

    report = {
        'engine': 'ChatterboxMultilingualTTS-v3-direct-reference',
        'source_speaker': 'reference audio (NOT Edge/Ahmet)',
        'reference_duration_seconds': round(duration, 3),
        'full_44s_reference_available': full_reference,
        'reference_sha256': hashlib.sha256(ref.read_bytes()).hexdigest(),
        'reference_window_seconds': 10,
        'human_approval_required': True,
        'voice_similarity_verified': False,
        'full_video_ready': False,
        'warning': ('Full 44-second reference supplied; listen to all candidates.' if full_reference
                    else 'Only the previous ~10-second excerpt is available. This is an exploratory audition, NOT a full-reference match.'),
        'clips': clips,
        'script': SAMPLE,
    }
    (output / 'voice_audition_v6.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps({k: v for k, v in report.items() if k not in ('script',)}, ensure_ascii=False), flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=Path('output/voice-audition'))
    args = p.parse_args()
    audition(args.output)

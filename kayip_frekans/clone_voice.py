"""Consent-based, offline Turkish voice cloning using MIT Chatterbox Multilingual V3.

Reference is provided only via GitHub Actions secret SERKAN_REFERENCE_MP3_B64;
it must NEVER be checked into a public repository, printed, or sent to ElevenLabs.
"""
import base64
import binascii
import os
from pathlib import Path
import subprocess
import tempfile
import wave

MODEL_NAME = 'Chatterbox Multilingual V3'
MODEL_LICENSE = 'MIT'
LANGUAGE = 'tr'
SECRET_NAME = 'SERKAN_REFERENCE_MP3_B64'


def require_reference(encoded=None):
    """Decode private 7-15s MP3 reference to a temporary mono WAV, or fail closed."""
    if encoded is None:
        encoded = os.environ.get(SECRET_NAME, '')
    if not encoded or len(encoded) > 48 * 1024:
        raise RuntimeError(f'{SECRET_NAME} GitHub Actions Secret eksik veya 48 KB sınırını aşıyor. Başka ses kullanılmadı.')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RuntimeError('Ses referansı bozuk Base64; seslendirme durduruldu.') from exc
    if len(data) < 1000 or len(data) > 37_000 or not (data.startswith(b'ID3') or data[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2')):
        raise RuntimeError('Ses referansı beklenen küçük MP3 dosyası değil.')
    temp_dir = tempfile.TemporaryDirectory(prefix='kf-voice-')
    folder = Path(temp_dir.name)
    source = folder / 'reference.mp3'
    source.write_bytes(data)
    source.chmod(0o600)
    destination = folder / 'reference.wav'
    try:
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
                        '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(destination)],
                       check=True, capture_output=True, timeout=45)
        with wave.open(str(destination), 'rb') as reader:
            duration = reader.getnframes() / reader.getframerate()
            if reader.getnchannels() != 1 or reader.getframerate() != 24000 or not 7 <= duration <= 15:
                raise RuntimeError('Referans 7-15 saniye, tek kanal 24 kHz olmalı.')
    except Exception:
        temp_dir.cleanup()
        raise
    return temp_dir, destination


def load_model():
    """Only Chatterbox v3 in Turkish; no silent substitute or external API."""
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    torch.set_num_threads(max(1, min(os.cpu_count() or 1, 4)))
    return ChatterboxMultilingualTTS.from_pretrained(device='cpu', t3_model='v3')


def synthesize(model, text, reference):
    if not text or len(text) > 340:
        raise ValueError('Ses parçası 1-340 karakter aralığında olmalı; metin kesilmedi.')
    import torch
    with torch.inference_mode():
        audio = model.generate(text, language_id=LANGUAGE,
                               audio_prompt_path=str(reference),
                               exaggeration=0.5, cfg_weight=0.35)
    if audio is None or audio.numel() < model.sr * 0.3:
        raise RuntimeError('Chatterbox ses üretmedi; başka sese geçilmedi.')
    return audio

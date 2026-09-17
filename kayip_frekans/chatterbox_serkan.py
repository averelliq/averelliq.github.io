"""Local/open-source Serkan voice cloning for KAYIP FREKANS_.

Uses Resemble AI Chatterbox Multilingual V3 on the GitHub Actions runner.
No ElevenLabs API calls or per-character credits are used here.
The reference audio stays outside the public repository and must be provided
at runtime via SERKAN_REFERENCE_URL or SERKAN_REFERENCE_B64.
"""
from __future__ import annotations

import base64
import math
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

_MODEL = None
_DEVICE = None


def reference_audio(out_dir: Path) -> Path:
    """Materialize the authorized voice reference without committing it publicly."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / 'serkan-reference.mp3'
    encoded = os.environ.get('SERKAN_REFERENCE_B64', '').strip()
    url = os.environ.get('SERKAN_REFERENCE_URL', '').strip()
    if encoded:
        try:
            payload = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise RuntimeError('SERKAN_REFERENCE_B64 geçerli base64 değil.') from exc
    elif url:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or not parsed.netloc:
            raise RuntimeError('SERKAN_REFERENCE_URL güvenli bir HTTPS adresi olmalı.')
        request = urllib.request.Request(url, headers={'User-Agent': 'KayipFrekansVoice/14'})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read(12 * 1024 * 1024 + 1)
    else:
        raise RuntimeError(
            'Serkan referans sesi eksik. SERKAN_REFERENCE_URL veya SERKAN_REFERENCE_B64 gerekli; '
            'başka sese geçilmedi.'
        )
    if len(payload) < 20_000 or len(payload) > 12 * 1024 * 1024:
        raise RuntimeError('Serkan referans ses dosyası beklenen boyutta değil.')
    dest.write_bytes(payload)
    return dest


def load_model(reference_path: Path):
    """Load once per workflow and cache speaker conditioning for every chunk."""
    global _MODEL, _DEVICE
    if _MODEL is not None:
        return _MODEL
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    torch.set_num_threads(max(1, min(4, os.cpu_count() or 2)))
    _DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = ChatterboxMultilingualTTS.from_pretrained(device=_DEVICE, t3_model='v3')
    model.prepare_conditionals(str(reference_path), exaggeration=0.46)
    _MODEL = model
    return model


def synthesize(text: str, reference_path: Path, wav_path: Path) -> float:
    """Generate one Turkish chunk with the cached cloned speaker identity."""
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        raise ValueError('Seslendirilecek metin boş.')
    if len(text) > 340:
        raise ValueError(f'Chatterbox parçası çok uzun: {len(text)} karakter.')
    model = load_model(reference_path)
    import torchaudio as ta

    wav = model.generate(
        text,
        language_id='tr',
        exaggeration=0.46,
        cfg_weight=0.34,
        temperature=0.72,
        repetition_penalty=1.22,
        min_p=0.05,
        top_p=1.0,
    )
    ta.save(str(wav_path), wav.cpu(), model.sr)
    info = ta.info(str(wav_path))
    duration = info.num_frames / info.sample_rate
    if not math.isfinite(duration) or duration <= 0.25:
        raise RuntimeError('Chatterbox geçerli ses üretemedi.')
    return duration


def estimated_word_boundaries(text: str, duration: float):
    """Duration-weighted word timing for subtitles when the local TTS exposes no timestamps."""
    matches = list(re.finditer(r'\S+', text))
    if not matches:
        raise ValueError('Altyazı için kelime bulunamadı.')
    weights = []
    for match in matches:
        token = match.group()
        letters = max(1, len(re.sub(r'[^0-9A-Za-zÇĞİÖŞÜçğıöşü]', '', token)))
        weight = max(0.7, letters ** 0.58)
        if re.search(r'[.!?…][\"”’\']*$', token):
            weight += 0.95
        elif re.search(r'[,;:][\"”’\']*$', token):
            weight += 0.40
        weights.append(weight)
    total_weight = sum(weights)
    cursor = 0.0
    result = []
    for match, weight in zip(matches, weights):
        span = duration * weight / total_weight
        start = cursor
        end = min(duration, cursor + span)
        result.append({
            'text': match.group(),
            'offset': round(start * 10_000_000),
            'duration': max(1, round((end - start) * 10_000_000)),
        })
        cursor = end
    return result

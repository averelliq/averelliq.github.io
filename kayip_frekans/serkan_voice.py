"""Exact ElevenLabs Serkan narrator with character-timed captions; never substitutes voices."""
import base64
import json
import os
import re
import urllib.error
import urllib.request

VOICE_ID = 'f4D8xroRt4ZvAzDe9FGL'
MODEL_ID = 'eleven_multilingual_v2'
URL = f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps?output_format=mp3_44100_128'


def require_key():
    key = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if not key:
        raise RuntimeError('ELEVENLABS_API_KEY eksik. Serkan yerine farklı ses kullanılmayacak; video durduruldu.')
    return key


def word_boundaries(text, alignment):
    """Convert ElevenLabs character timestamps into Edge-compatible word timings."""
    chars = alignment.get('characters')
    starts = alignment.get('character_start_times_seconds')
    ends = alignment.get('character_end_times_seconds')
    if not isinstance(chars, list) or ''.join(chars) != text:
        raise ValueError('ElevenLabs zamanlaması metinle eşleşmiyor; altyazı tahmin edilmedi.')
    if not (len(chars) == len(starts or []) == len(ends or [])):
        raise ValueError('ElevenLabs karakter zamanlaması eksik.')
    result = []
    previous = 0.0
    for token in re.finditer(r'\S+', text):
        s, e = token.span()
        begin, finish = float(starts[s]), float(ends[e - 1])
        if not (0 <= previous <= begin < finish):
            raise ValueError('ElevenLabs zamanlama sırası bozuk.')
        result.append({'text': token.group(), 'offset': round(begin * 10_000_000),
                       'duration': round((finish - begin) * 10_000_000)})
        previous = begin
    if not result:
        raise ValueError('Seslendirilecek kelime yok.')
    return result


def synthesize(text, *, previous_text='', next_text='', opener=None):
    """Generate original Serkan voice, returning MP3 bytes and actual word boundaries.

    opener is injectable for offline tests. Only the explicitly selected voice ID is used.
    """
    key = require_key()
    payload = {
        'text': text,
        'model_id': MODEL_ID,
        'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75,
                           'style': 0.0, 'use_speaker_boost': True, 'speed': 1.0},
    }
    if previous_text:
        payload['previous_text'] = previous_text[-1000:]
    if next_text:
        payload['next_text'] = next_text[:1000]
    request = urllib.request.Request(
        URL, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'xi-api-key': key, 'Content-Type': 'application/json'}, method='POST',
    )
    try:
        with (opener or urllib.request.urlopen)(request, timeout=180) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'ElevenLabs Serkan seslendirmesi HTTP {error.code} ile başarısız; başka sese geçilmedi.') from None
    if not isinstance(data, dict) or not data.get('audio_base64'):
        raise RuntimeError('ElevenLabs Serkan MP3 döndürmedi; üretim durduruldu.')
    boundaries = word_boundaries(text, data.get('alignment') or {})
    try:
        audio = base64.b64decode(data['audio_base64'], validate=True)
    except (ValueError, TypeError) as error:
        raise RuntimeError('ElevenLabs ses verisi bozuk.') from error
    if len(audio) < 100:
        raise RuntimeError('ElevenLabs ses dosyası beklenenden küçük.')
    return audio, boundaries

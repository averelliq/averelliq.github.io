"""Offline tests: no paid ElevenLabs calls, no credentials required in CI."""
import base64
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import brand_logo
import serkan_voice as voice


class TestSerkanVoice(unittest.TestCase):
    def test_exact_voice_and_endpoint(self):
        self.assertEqual(voice.VOICE_ID, 'f4D8xroRt4ZvAzDe9FGL')
        self.assertIn('/' + voice.VOICE_ID + '/with-timestamps', voice.URL)

    def test_no_api_key_never_falls_back(self):
        with mock.patch.dict(os.environ, {'ELEVENLABS_API_KEY': ''}):
            with self.assertRaisesRegex(RuntimeError, 'ELEVENLABS_API_KEY'):
                voice.synthesize('Merhaba.')

    def test_character_alignment_preserves_turkish_and_punctuation(self):
        text = 'Kapı açıldı. Üç ses!'
        alignment = {
            'characters': list(text),
            'character_start_times_seconds': [i * .06 for i in range(len(text))],
            'character_end_times_seconds': [(i + 1) * .06 for i in range(len(text))],
        }
        words = voice.word_boundaries(text, alignment)
        self.assertEqual([x['text'] for x in words], ['Kapı', 'açıldı.', 'Üç', 'ses!'])
        self.assertTrue(all(x['duration'] > 0 for x in words))
        bad = dict(alignment, characters=list('Başka metin'))
        with self.assertRaisesRegex(ValueError, 'eşleşmiyor'):
            voice.word_boundaries(text, bad)

    def test_api_payload_has_only_selected_voice(self):
        text = 'Kapı açıldı.'
        alignment = {
            'characters': list(text),
            'character_start_times_seconds': [i * .04 for i in range(len(text))],
            'character_end_times_seconds': [(i + 1) * .04 for i in range(len(text))],
        }
        response = {'audio_base64': base64.b64encode(b'x' * 512).decode(),
                    'alignment': alignment}
        captured = []

        def fake_open(request, timeout):
            captured.append((request.full_url, json.loads(request.data.decode('utf-8')),
                             request.get_header('Xi-api-key')))
            return io.BytesIO(json.dumps(response).encode())

        with mock.patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test-not-real'}):
            audio, words = voice.synthesize(text, opener=fake_open)
        self.assertEqual(len(audio), 512)
        self.assertEqual(words[0]['text'], 'Kapı')
        self.assertIn(voice.VOICE_ID, captured[0][0])
        self.assertEqual(captured[0][1]['model_id'], 'eleven_multilingual_v2')
        self.assertEqual(captured[0][1]['voice_settings']['stability'], .5)
        self.assertEqual(captured[0][2], 'test-not-real')

    def test_original_logo_is_valid_embedded_png(self):
        from PIL import Image
        image = Image.open(io.BytesIO(brand_logo.logo_png()))
        image.verify()
        self.assertGreaterEqual(image.width, 100)
        self.assertEqual(image.width, image.height)


if __name__ == '__main__':
    unittest.main()

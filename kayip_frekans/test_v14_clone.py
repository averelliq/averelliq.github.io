"""Fast tests: no network, no model downloads, no real voice data or secrets."""
import base64
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

import clone_voice
import cloud_v14


class CloneVoiceTests(unittest.TestCase):
    def test_no_secret_fails_without_fallback(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'SERKAN_REFERENCE_MP3_B64'):
                clone_voice.require_reference()

    def test_invalid_base64_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'Base64'):
            clone_voice.require_reference('%%%')

    def test_decodes_reference_into_private_temporary_wav(self):
        sample = base64.b64encode(b'ID3' + b'\0' * 1900).decode()
        def fake_ffmpeg(args, **kwargs):
            with wave.open(args[-1], 'wb') as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(24000)
                output.writeframes(b'\0\0' * 24000 * 10)
        with mock.patch('clone_voice.subprocess.run', side_effect=fake_ffmpeg):
            folder, wav = clone_voice.require_reference(sample)
            try:
                self.assertTrue(wav.exists())
                self.assertEqual(wav.stat().st_mode & 0o777, 0o644)
                self.assertEqual((wav.parent / 'reference.mp3').stat().st_mode & 0o777, 0o600)
            finally:
                folder.cleanup()
            self.assertFalse(wav.exists())

    def test_subtitle_timings_marked_approximate(self):
        words = cloud_v14.approximate_boundaries('Kapıyı açma. Ses hâlâ orada.', 4.0)
        self.assertEqual(len(words), 5)
        self.assertTrue(all(0 <= w['offset'] < 40_000_000 for w in words))
        self.assertTrue(all(w['duration'] > 0 for w in words))

    def test_cloned_voice_is_only_narrator(self):
        self.assertIs(cloud_v14.v3.narrate, cloud_v14.narrate_clone)
        self.assertEqual(clone_voice.LANGUAGE, 'tr')
        self.assertEqual(clone_voice.MODEL_LICENSE, 'MIT')


if __name__ == '__main__':
    unittest.main()

"""Regression checks for size-safe PRIVATE reference transport."""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import voice_preview_v6 as voice


class PrivateReferenceTransportTests(unittest.TestCase):
    def test_complete_private_reference_is_reassembled_before_tts(self):
        raw = b'OggS' + b'private-opus-test' * 30
        value = base64.b64encode(raw).decode('ascii')
        n = len(value) // 3
        env = {f'KF_REF_OPUS_B64_{i}': part for i, part in enumerate(
            (value[:n], value[n:2*n], value[2*n:]), 1)}
        with TemporaryDirectory() as folder:
            with patch.dict(os.environ, env, clear=True), \
                 patch.object(voice, 'EXPECTED_OPUS_SHA256', hashlib.sha256(raw).hexdigest()), \
                 patch.object(voice, 'probe_seconds', return_value=44.45):
                path, private = voice.load_reference(Path(folder), Path(folder)/'fallback.mp3')
            self.assertTrue(private)
            self.assertEqual(path.name, 'reference-full-private.opus')
            self.assertEqual(path.read_bytes(), raw)

    def test_one_missing_secret_must_fail_instead_of_using_public_excerpt(self):
        with TemporaryDirectory() as folder, \
             patch.dict(os.environ, {'KF_REF_OPUS_B64_1': 'T2dnUw=='}, clear=True):
            with self.assertRaisesRegex(ValueError, 'all 3'):
                voice.load_reference(Path(folder), Path(folder)/'fallback.mp3')

    def test_wrong_voice_reference_hash_is_rejected(self):
        value = base64.b64encode(b'OggS' + b'wrong-sound').decode('ascii')
        with TemporaryDirectory() as folder, patch.dict(os.environ, {
            'KF_REF_OPUS_B64_1': value[:5],
            'KF_REF_OPUS_B64_2': value[5:10],
            'KF_REF_OPUS_B64_3': value[10:],
        }, clear=True):
            with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
                voice.load_reference(Path(folder), Path(folder)/'fallback.mp3')

    def test_old_oversized_single_secret_has_clear_error(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {
            'KF_FULL_REFERENCE_B64': 'A' * (48*1024),
        }, clear=True):
            with self.assertRaisesRegex(ValueError, '48KB'):
                voice.load_reference(Path(folder), Path(folder)/'fallback.mp3')


if __name__ == '__main__':
    unittest.main()

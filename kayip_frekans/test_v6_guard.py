from __future__ import annotations

import unittest
from unittest.mock import patch

import visual_balance_v5 as visuals
import voice_preview_v6 as voice


class V6GuardTests(unittest.TestCase):
    def test_voice_duration_invalid_is_rejected(self):
        with patch.object(voice.subprocess, 'check_output', return_value='nan'):
            with self.assertRaises(ValueError):
                voice.probe_seconds(voice.Path('missing.mp3'))

    def test_voice_preview_has_three_explicit_variants(self):
        self.assertEqual(len(voice.SETTINGS), 3)
        self.assertTrue(all(0 <= cfg <= 1 and 0 <= exaggeration <= 1
                            for _, exaggeration, cfg in voice.SETTINGS))
        self.assertIn('dolabın', voice.SAMPLE)

    def test_door_does_not_override_explicit_wardrobe(self):
        s = [{'start':0, 'end':5, 'text':'Kapıyı kapattım. Birden dolabın kapağı açıldı.'}]
        visuals.balance(s)
        self.assertEqual(s[0]['kind'], 'room')
        self.assertEqual(visuals.validate(s)['scene_count'], 1)

    def test_no_hallucinated_forest(self):
        scenes = [{'start':i*5, 'end':(i+1)*5,
                   'text':'Koridor boştu. Kapının kilidine dokundum.'}
                  for i in range(8)]
        visuals.balance(scenes)
        self.assertFalse(any(s['kind']=='forest' for s in scenes))
        self.assertEqual(visuals.validate(scenes)['scene_count'],8)

    def test_reject_unsupported_scene_subject(self):
        scene = [{'start':0,'end':3,'text':'Mutfaktaki dolabı açtım.','kind':'forest'}]
        with self.assertRaisesRegex(ValueError,'unsupported image subject'):
            visuals.validate(scene)

    def test_reject_zero_length_scene(self):
        scene = [{'start':3,'end':3,'text':'Pencereden baktım.','kind':'window'}]
        with self.assertRaisesRegex(ValueError,'invalid duration'):
            visuals.validate(scene)


if __name__ == '__main__':
    unittest.main()

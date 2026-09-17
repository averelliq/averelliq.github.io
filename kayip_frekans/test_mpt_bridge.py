"""Preflight tests; no MPT installation, paid API or voice cloning required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import wave

from PIL import Image
import mpt_bridge as bridge


class MptBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'assets').mkdir()
        self.story = ('Kapıyı açtığımda içeride kimse yoktu. Ama kardeşimin sesi '
                      'gece boyunca koridorun sonunda yankılandı. ') * 5
        (self.root / 'story.txt').write_text(self.story, encoding='utf-8')
        self.audio = self.root / 'narration.wav'
        with wave.open(str(self.audio), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(b'\0\0' * (24000 * 30))
        self.approval = {
            'approved_by_user': True,
            'voice_label': 'Serkan Demirci',
            'audio_sha256': hashlib.sha256(self.audio.read_bytes()).hexdigest(),
        }
        self.write_approval()
        self.scenes = []
        for i in range(3):
            asset = self.root / 'assets' / f'scene{i+1}.png'
            Image.new('RGB', (1280, 720), (25 + i*45, 10+i*40, 45+i*35)).save(asset)
            self.scenes.append({
                'start': 10 * i, 'end': 10 * (i+1),
                'kind': ['corridor', 'door', 'room'][i],
                'description': f'Onaylanmış gerçek hikâye karesi {i+1}',
                'asset': f'assets/{asset.name}',
                'approved_by_user': True,
            })
        self.write_scenes()

    def write_approval(self):
        (self.root / 'approval.json').write_text(json.dumps(self.approval), encoding='utf-8')

    def write_scenes(self):
        (self.root / 'scenes.json').write_text(json.dumps(self.scenes), encoding='utf-8')

    def ready(self):
        return bridge.prepare(self.root, min_seconds=20, max_seconds=40)

    def test_preflight_accepts_exact_approved_audio_and_three_scenes(self):
        plan = self.ready()
        self.assertEqual(plan['scene_count'], 3)
        command = bridge.command(plan, self.root)
        self.assertIn('--custom-audio-file', command)
        self.assertEqual(command[command.index('--voice-name')+1], 'no-voice')
        self.assertEqual(command[command.index('--video-source')+1], 'local')
        self.assertIn('--no-subtitle-enabled', command)
        self.assertNotIn('--confirm-wavespeed-charge', command)
        self.assertEqual(command[command.index('--video-aspect')+1], '16:9')

    def test_missing_approval_fails_closed(self):
        self.approval['approved_by_user'] = False
        self.write_approval()
        with self.assertRaisesRegex(ValueError, 'not been explicitly approved'):
            self.ready()

    def test_other_voice_label_rejected(self):
        self.approval['voice_label'] = 'Ahmet'
        self.write_approval()
        with self.assertRaisesRegex(ValueError, 'Serkan'):
            self.ready()

    def test_tampered_audio_is_rejected(self):
        with self.audio.open('ab') as f:
            f.write(b'CHANGED')
        with self.assertRaisesRegex(ValueError, 'hash does not match'):
            self.ready()

    def test_visual_unapproved_rejected(self):
        self.scenes[1]['approved_by_user'] = False
        self.write_scenes()
        with self.assertRaisesRegex(ValueError, 'not visually approved'):
            self.ready()

    def test_visual_timeline_gap_rejected(self):
        self.scenes[1]['start'] = 11
        self.write_scenes()
        with self.assertRaisesRegex(ValueError, 'gap/overlap'):
            self.ready()

    def test_exact_visual_duplicates_with_different_names_rejected(self):
        duplicate = (self.root/'assets'/'scene1.png').read_bytes()
        for i in (1, 2):
            (self.root/'assets'/f'scene{i+1}.png').write_bytes(duplicate)
        with self.assertRaisesRegex(ValueError, 'reused more than twice'):
            self.ready()

    def test_traversal_rejected(self):
        self.scenes[0]['asset'] = 'assets/../../private.mp4'
        self.write_scenes()
        with self.assertRaisesRegex(ValueError, 'unsafe/unsupported'):
            self.ready()

    def test_no_approved_long_audio_cannot_run_as_15min(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            bridge.prepare(self.root)

    def test_long_scene_rejected(self):
        self.scenes[0]['end'] = 26
        self.write_scenes()
        with self.assertRaisesRegex(ValueError, '3-25'):
            self.ready()

    def test_low_resolution_rejected(self):
        Image.new('RGB', (500, 300)).save(self.root/'assets'/'scene2.png')
        with self.assertRaisesRegex(ValueError, 'low resolution'):
            self.ready()


if __name__ == '__main__':
    unittest.main()

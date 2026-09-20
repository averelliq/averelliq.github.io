import json
import unittest
from unittest.mock import patch
import bot


class BotTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            'source': 'pexels', 'pexels_video_id': 123, 'title': 'Rusty Tool Restored #Shorts',
            'item': 'rusty tool', 'observed_steps': ['the surface is cleaned',
            'the rust is carefully removed', 'the tool is reassembled'],
            'human_reviewed': True, 'rights_reviewed': True,
            'burned_in_captions_or_watermark': False, 'visible_before_and_after': True,
            'start_seconds': 0, 'target_seconds': 45,
        }

    def test_manifest_requires_review(self):
        self.manifest['human_reviewed'] = False
        with self.assertRaisesRegex(ValueError, 'review'):
            bot.validate_manifest(self.manifest)

    def test_manifest_rejects_embedded_caption(self):
        self.manifest['burned_in_captions_or_watermark'] = True
        with self.assertRaisesRegex(ValueError, 'embedded'):
            bot.validate_manifest(self.manifest)

    def test_manifest_rejects_short_video(self):
        self.manifest['target_seconds'] = 32
        with self.assertRaisesRegex(ValueError, '40-50'):
            bot.validate_manifest(self.manifest)

    def test_narration_tracks_observed_steps(self):
        text = bot.narration(bot.validate_manifest(self.manifest))
        self.assertIn('rust is carefully removed', text)
        self.assertIn('reassembled', text)
        self.assertNotIn('electrolysis', text)

    def test_only_hd_mp4(self):
        source = {'video_files': [
            {'file_type': 'video/mp4', 'width': 640, 'height': 360, 'link': 'https://example.com/sd'},
            {'file_type': 'video/mp4', 'width': 1080, 'height': 1920, 'link': 'https://example.com/hd'},
        ]}
        self.assertEqual(bot.select_mp4(source), 'https://example.com/hd')

    @patch('bot.pexels_json')
    def test_discover_filters_short_footage(self, client):
        client.return_value = {'videos': [
            {'id': 1, 'duration': 25, 'video_files': [{'link': 'https://a'}]},
            {'id': 2, 'duration': 45, 'video_files': [{'link': 'https://b'}]},
        ]}
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'candidates.json'
            bot.discover(target)
            ids = [entry['id'] for entry in json.loads(target.read_text())]
        self.assertEqual(ids, [2])
        self.assertEqual(client.call_count, len(bot.SEARCH_TERMS))


if __name__ == '__main__':
    unittest.main()

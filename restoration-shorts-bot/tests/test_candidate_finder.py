import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import candidate_finder as finder


class CandidateFinderTests(unittest.TestCase):
    def video(self, number, slug, duration=75):
        return {'id': number, 'url': f'https://www.pexels.com/video/{slug}-{number}/',
                'duration': duration, 'video_files': [{'file_type': 'video/mp4'}],
                'image': 'https://images.pexels.com/photos/1.jpg', 'user': {'name': 'Contributor'}}

    def test_generic_factory_filtered(self):
        self.assertLess(finder.score(self.video(1, 'person-wiping-metal'), 'rusty restoration')[0], 0)
        self.assertLess(finder.score(self.video(2, 'worker-grinding-machine'), 'rusty restoration')[0], 0)

    def test_explicit_restoration_higher_than_weak(self):
        strong = finder.score(self.video(1, 'restoring-rusty-iron'), 'rusty iron restoration')[0]
        weak = finder.score(self.video(2, 'antique-iron'), 'rusty iron restoration')[0]
        self.assertGreater(strong, weak)
        self.assertGreater(weak, 0)

    @patch('candidate_finder.bot.pexels_json')
    def test_outputs_reviewable_leads_never_approves(self, client):
        client.return_value = {'videos': [
            self.video(1, 'person-wiping-metal'),
            self.video(2, 'antique-iron'),
            self.video(3, 'restoring-rusty-iron'),
            self.video(4, 'rusty-iron', 12),
        ]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'candidates.json'
            finder.discover(output)
            candidates = json.loads(output.read_text(encoding='utf-8'))
            report = json.loads((output.parent / 'review_report.json').read_text(encoding='utf-8'))
            gallery = (output.parent / 'review_gallery.html').read_text(encoding='utf-8')
        self.assertEqual([item['id'] for item in candidates], [3, 2])
        self.assertEqual(report['visually_verified'], 0)
        self.assertEqual(report['approved_for_reuse'], 0)
        self.assertIn('unverified', gallery.lower())
        self.assertEqual(client.call_count, len(finder.style_bot.SEARCH_TERMS))


if __name__ == '__main__':
    unittest.main()

"""Offline US trend tests; no real YouTube/Gemini calls and no uploads."""
from __future__ import annotations

import os
import unittest
from unittest import mock

import trend_ideas
import us_trends


RSS = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item><title>Senate election results</title></item>
  <item><title>Why popcorn pops</title></item>
  <item><title>Ice cream sales surge</title></item>
  <item><title>Basketball scores and injuries</title></item>
</channel></rss>'''


class FakeResponse:
    content = RSS

    def raise_for_status(self):
        return None


class USSubjectTests(unittest.TestCase):
    def setUp(self):
        trend_ideas._CACHE.clear()
        trend_ideas._REFERENCES.clear()

    def test_google_us_feed_rejects_politics_scores_and_injuries(self):
        with mock.patch.object(us_trends.requests, 'get', return_value=FakeResponse()) as get:
            actual = us_trends._us_search_terms('everyday')
        self.assertEqual(set(actual), {'Why popcorn pops', 'Ice cream sales surge'})
        self.assertEqual(get.call_args.args[0], us_trends.US_TRENDS_RSS)

    def test_no_video_key_and_no_google_trend_uses_us_evergreen(self):
        us_trends.install()
        with mock.patch.dict(os.environ, {'YT_DATA_API_KEY': '', 'SHORTS_US_TRENDS': '1'}):
            with mock.patch.object(us_trends, '_us_search_terms', return_value=[]):
                subject = trend_ideas.pick_topic('everyday', lambda theme: 'global generic',
                                                 lambda prompt: {'suitable': False, 'topic': ''})
        self.assertIn(subject, us_trends.US_FALLBACKS['everyday'])
        self.assertIsNone(trend_ideas.reference_for('everyday'))

    def test_eligible_us_search_term_produces_original_subject_and_provenance(self):
        us_trends.install()
        def original_topic(prompt):
            self.assertIn('Why popcorn pops', prompt)
            return {'suitable': True, 'topic': 'why popcorn kernels pop'}
        with mock.patch.dict(os.environ, {'YT_DATA_API_KEY': '', 'SHORTS_US_TRENDS': '1'}):
            with mock.patch.object(us_trends, '_us_search_terms', return_value=['Why popcorn pops']):
                subject = trend_ideas.pick_topic('everyday', lambda theme: 'global generic', original_topic)
        self.assertEqual(subject, 'why popcorn kernels pop')
        reference = trend_ideas.reference_for('everyday')
        self.assertEqual(reference['region'], 'US')
        self.assertIn('search interest', reference['source'].lower())
        self.assertNotIn('observed_views', reference)


if __name__ == '__main__':
    unittest.main()

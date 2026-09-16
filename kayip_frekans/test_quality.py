"""Run with: python -m unittest discover -s kayip_frekans -p 'test_*.py'"""
import tempfile
import unittest
from pathlib import Path

from quality import (INTRO_CTA, INTRO_END, INTRO_OPEN, clean_title,
                     intro_text, normalize_for_speech, validate_story,
                     write_quality_report)


class QualityTests(unittest.TestCase):
    def test_intro_contains_mandatory_brand_and_call_to_action(self):
        text = intro_text('Kapının Ardındaki Ses — Üretim Testi')
        self.assertTrue(text.startswith(INTRO_OPEN))
        self.assertIn('Bugünkü hikâyemizin adı: Kapının Ardındaki Ses.', text)
        self.assertIn(INTRO_CTA, text)
        self.assertTrue(text.endswith(INTRO_END))
        self.assertNotIn('Üretim Testi', text)

    def test_clock_readings(self):
        text = normalize_for_speech('03:15 ve 22:30, sonra 12:00.')
        self.assertIn('gece üç on beş', text)
        self.assertIn('gece on buçuk', text)
        self.assertIn('öğleden sonra on iki', text)
        self.assertNotIn('03:15', text)

    def test_invalid_clock_not_changed(self):
        self.assertEqual(normalize_for_speech('Saat 25:77.'), 'Saat 25:77.')

    def test_short_story_rejected_before_render(self):
        with self.assertRaisesRegex(ValueError, 'çok kısa'):
            validate_story('Başlık', ['Kısa bir hikâye bitti.'], 30, False)

    def test_duplicate_chapter_rejected(self):
        passage = 'Gece yarısı kapıyı açtığımda kimseyi görmedim. ' * 15
        with self.assertRaisesRegex(ValueError, 'Tekrarlanan'):
            validate_story('Başlık', [passage, passage], 5, True)

    def test_final_story_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Final Story'):
            validate_story('Başlık', ['Final Story. ' * 40], 5, True)

    def test_successful_test_report(self):
        passage = 'Kapının arkasından gelen ses annemin sesiydi. ' * 8
        parts, report = validate_story('Kapı', [passage], 5, True)
        self.assertTrue(report['human_review_required'])
        self.assertEqual(len(parts), 1)
        with tempfile.TemporaryDirectory() as tmp:
            written = write_quality_report(tmp, report, 42.4)
            self.assertTrue(Path(tmp, 'quality_report.json').exists())
            self.assertFalse(written['youtube_uploaded'])
            self.assertEqual(written['measured_video_seconds'], 42.4)

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            clean_title('— Üretim Testi')


if __name__ == '__main__':
    unittest.main()

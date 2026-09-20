import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "long_to_short.py"
spec = importlib.util.spec_from_file_location("long_to_short", MODULE)
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)


class LongToShortTests(unittest.TestCase):
    def test_ten_minutes_kept_in_order_at_roughly_ten_times_speed(self):
        filtergraph = bot.build_filter(600, 59.9, None)
        self.assertIn('setpts=(PTS-STARTPTS)/10.016694490818', filtergraph)
        self.assertIn('fps=30', filtergraph)
        self.assertNotIn('select=', filtergraph)
        self.assertNotIn('concat=', filtergraph)

    def test_keeps_entire_frame_with_background(self):
        graph = bot.build_filter(600, 59.9, None)
        self.assertIn('force_original_aspect_ratio=decrease', graph)
        self.assertIn('overlay=(W-w)/2:(H-h)/2', graph)

    def test_exact_burned_in_subtitle_rectangle(self):
        box = bot.parse_subtitle_box('10:50:200:40', 320, 180)
        self.assertEqual(box, 'delogo=x=10:y=50:w=200:h=40')
        self.assertIn('delogo=x=10:y=50:w=200:h=40', bot.build_filter(100, 59, box))

    def test_reject_subtitle_rectangle_outside_source(self):
        with self.assertRaises(ValueError):
            bot.parse_subtitle_box('200:150:200:40', 320, 180)

    def test_does_not_claim_burned_subtitles_removed_by_default(self):
        self.assertIsNone(bot.parse_subtitle_box('none', 320, 180))


if __name__ == '__main__':
    unittest.main()

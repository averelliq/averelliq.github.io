"""Offline tests: no real network, credentials or YouTube publication."""
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

NAMES = ("creator_guard", "hd_footage_guard", "quality_entry", "selection_guard",
         "stock_recovery", "trend_ideas", "upgrade", "visual_guard")
for name in NAMES:
    sys.modules.setdefault(name, types.ModuleType(name))
source = Path(__file__).resolve().parents[1] / "footage_first.py"
spec = importlib.util.spec_from_file_location("footage_first_unit", source)
ff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ff)


class DummyFile:
    def unlink(self, **kwargs):
        pass


class FootageFirstTests(unittest.TestCase):
    def test_one_off_never_substitutes_a_different_topic(self):
        with patch.dict(os.environ, {"SHORTS_ONE_OFF_PUBLISH": "1"}):
            self.assertEqual(len(ff._candidates("everyday", "why airplane windows are rounded")), 1)
            with self.assertRaises(ValueError):
                ff._candidates("everyday", "unknown one-off topic")

    def test_scheduled_subject_can_fall_back_to_filmable_ideas(self):
        with patch.dict(os.environ, {"SHORTS_ONE_OFF_PUBLISH": "0"}):
            topics = ff._candidates("everyday", "a subject with no usable footage")
        self.assertTrue(any(topic == "how an espresso machine brews coffee" for topic, _ in topics))

    def test_eight_unique_approved_clips_are_mandatory_before_script(self):
        pool = [{"id": i, "file_urls": ["https://example.invalid"], "query": "test",
                 "url": "https://www.pexels.com/video/test/"} for i in range(10)]
        def download(candidate, position):
            fingerprint = int.from_bytes(bytes([position + 1]) * 8, "big")
            return dict(candidate, fingerprint=fingerprint, path=DummyFile(),
                        previews=[b"frame"] * 3)
        with patch.object(ff, "_search", return_value=pool), \
             patch.object(ff, "_download", side_effect=download), \
             patch.object(ff, "_vision", return_value=[True] * 10):
            self.assertEqual(len(ff._prepare("test", ("test",))), 8)
        with patch.object(ff, "_search", return_value=pool), \
             patch.object(ff, "_download", side_effect=download), \
             patch.object(ff, "_vision", return_value=[True] * 7 + [False] * 3):
            self.assertIsNone(ff._prepare("test", ("test",)))


if __name__ == "__main__":
    unittest.main(verbosity=2)

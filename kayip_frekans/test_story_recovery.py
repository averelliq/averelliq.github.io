"""Fast offline tests; no Ollama, Pexels, TTS or video upload required."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mpt_reference_style
import mpt_story_recovery


class RecoveryTests(unittest.TestCase):
    def test_supernatural_events_are_not_prohibited(self):
        self.assertIn("Cin görünmesi, kapı çarpması, çığlık", mpt_reference_style.STYLE_BRIEF)
        self.assertIn("ASLA tek başına kusur değildir", mpt_reference_style.quality_prompt("Cin gördüm.", "köy", 15))

    def test_bad_chapter_is_rewritten_not_silently_accepted(self):
        responses = iter(["bozuk metin", "Gece köydeki kapı içeriden çarptı ve kardeşimin sesini duydum."])
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(mpt_story_recovery.cloud_v3, "check_passage", side_effect=[
                ValueError("ilk taslak hatalı"),
                "Gece köydeki kapı içeriden çarptı ve kardeşimin sesini duydum.",
            ]):
                result = mpt_story_recovery._passage(
                    "Köy evi", 5, 100, lambda prompt: next(responses), Path(folder)
                )
            self.assertIn("kapı", result)
            self.assertTrue((Path(folder) / "accepted.txt").is_file())
            self.assertTrue((Path(folder) / "last_failure.txt").is_file())

    def test_four_failed_chapter_attempts_trigger_new_outline(self):
        count = 0
        outlines = 0
        def fake_ask(prompt, structured=False):
            nonlocal count, outlines
            if "Tam JSON şeması" in prompt:
                outlines += 1
                return {
                    "title": "Köydeki Ses", "characters": "Ali ve ölen kardeşi",
                    "setting": "Bir köy evi", "rules": "Ses kapalı kapıdan gelir",
                    "clues": "Saat ve eski fotoğraf",
                    "chapters": [f"Olaylar tutarlı gelişiyor; bölüm {i}" for i in range(12)],
                }
            if structured and '"issues"' in prompt:
                return {"issues": [], "pass": True}
            count += 1
            if outlines == 1:
                raise RuntimeError("geçici model kesintisi")
            return "Gece köy evinin kilitli kapısı çarptı, sonra kardeşimin sesi duyuldu."
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(mpt_story_recovery.cloud_v3, "check_passage", side_effect=lambda text, a, b: text), \
                 patch.object(mpt_story_recovery.time, "sleep", return_value=None):
                title, parts, report = mpt_story_recovery.generate_story(
                    "Köy evi", 15, fake_ask, Path(folder), max_story_attempts=2
                )
            self.assertEqual(outlines, 2)
            self.assertEqual(count, 16)
            self.assertEqual(len(parts), 13)
            self.assertEqual(report["story_attempt"], 2)
            self.assertTrue((Path(folder) / "recovery" / "story-1" / "failure.txt").is_file())
            self.assertTrue((Path(folder) / "recovery" / "story-2" / "story_only.txt").is_file())
            self.assertIn("Köydeki Ses", title)


if __name__ == "__main__":
    unittest.main()

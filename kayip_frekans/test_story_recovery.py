"""Offline tests for KAYIP FREKANS story recovery, without Ollama or video."""
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

    def test_incomplete_outline_is_expanded_not_rejected(self):
        def short_outline(prompt, structured=False):
            return {"title": "Ölen Kardeşimin Sesi", "characters": "İki kardeş ve komşu",
                    "setting": "Köy evi", "rules": "Kapı kilitli kalır", "clues": "Eski saat",
                    "chapters": ["Kilitli kapıdan tanıdık ses duyulur", "Komşu eski saatin sırrını açıklar",
                                 "Görünmeyen varlık eve girer", "Saat ve kardeşin sesi finalde birleşir"]}
        plan = mpt_story_recovery._outline("Köydeki kapı", 12, short_outline, "")
        self.assertEqual(len(plan["chapters"]), 12)
        self.assertEqual(plan["outline_source_beats"], 4)
        self.assertEqual(plan["outline_mode"], "model_beats_expanded")
        self.assertEqual(len(set(plan["chapters"])), 12)
        self.assertIn("final", plan["chapters"][-1].lower())

    def test_empty_outline_uses_story_scaffold_not_fake_narration(self):
        plan = mpt_story_recovery._outline(
            "Ölen kardeşimin sesi kilitli kapıdan geldi", 12,
            lambda prompt, structured=False: {"chapters": []}, "")
        self.assertEqual(plan["outline_mode"], "topic_grounded_scaffold")
        self.assertEqual(len(plan["chapters"]), 12)
        self.assertIn("final", plan["chapters"][-1].lower())

    def test_bad_chapter_is_rewritten_not_silently_accepted(self):
        responses = iter(["bozuk metin", "Gece köydeki kapı içeriden çarptı ve kardeşimin sesini duydum."])
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(mpt_story_recovery.cloud_v3, "check_passage", side_effect=[
                ValueError("ilk taslak hatalı"),
                "Gece köydeki kapı içeriden çarptı ve kardeşimin sesini duydum.",
            ]):
                result = mpt_story_recovery._passage("Köy evi", 5, 100, lambda p: next(responses), Path(folder))
            self.assertIn("kapı", result)
            self.assertTrue((Path(folder) / "accepted.txt").is_file())
            self.assertTrue((Path(folder) / "last_failure.txt").is_file())

    def test_irrelevant_editor_json_retries_without_rewriting_chapters(self):
        replies = iter([{"title": "Karanlığın Yankıları", "author": "AI"},
                        {}, {"pass": True, "issues": []}])
        with tempfile.TemporaryDirectory() as folder:
            draft = Path(folder)
            result = mpt_story_recovery._review_story(
                "Kapı çarptı, kardeşimin sesini duydum.",
                lambda prompt, structured=False: next(replies), draft)
            self.assertEqual(result["status"], "verified_by_local_editor")
            self.assertEqual(result["attempts"], 3)
            self.assertTrue((draft / "editor_review_attempt_1.json").exists())
            self.assertFalse((draft / "editor_unavailable.json").exists())

    def test_editor_wrong_schema_never_claims_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            draft = Path(folder)
            result = mpt_story_recovery._review_story(
                "İlk ipucu eski saat, son ipucu eski saat.",
                lambda prompt, structured=False: {"title": "Yanlış şema"}, draft)
            self.assertIsNone(result["pass"])
            self.assertTrue(result["requires_independent_quality_gate"])
            self.assertTrue((draft / "editor_unavailable.json").exists())

    def test_concrete_editor_issue_still_blocks_bad_story(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(mpt_story_recovery.StoryExhausted):
                mpt_story_recovery._review_story(
                    "Karakterin ismi başta Ali sonda Ayşe oldu.",
                    lambda prompt, structured=False: {
                        "issues": ["Anlatıcının ismi gerekçesiz Ali'den Ayşe'ye değişiyor"],
                        "pass": False}, Path(folder))

    def test_four_failed_chapter_attempts_trigger_new_outline(self):
        count, outlines = 0, 0
        def fake_ask(prompt, structured=False):
            nonlocal count, outlines
            if "Tam JSON şeması" in prompt:
                outlines += 1
                return {"title": "Köydeki Ses", "characters": "Ali ve ölen kardeşi",
                        "setting": "Bir köy evi", "rules": "Ses kapalı kapıdan gelir",
                        "clues": "Saat ve eski fotoğraf",
                        "chapters": [f"Olaylar tutarlı gelişiyor; bölüm {i}" for i in range(12)]}
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
                    "Köy evi", 15, fake_ask, Path(folder), max_story_attempts=2)
            self.assertEqual(outlines, 2)
            self.assertEqual(count, 16)
            self.assertEqual(len(parts), 13)
            self.assertEqual(report["story_attempt"], 2)
            self.assertTrue(report["independent_quality_gate_required"])
            self.assertTrue((Path(folder) / "recovery" / "story-1" / "failure.txt").is_file())
            self.assertTrue((Path(folder) / "recovery" / "story-2" / "story_only.txt").is_file())
            self.assertIn("Köydeki Ses", title)


if __name__ == "__main__":
    unittest.main()

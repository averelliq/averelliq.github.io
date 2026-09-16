"""Offline checks for visual selection; no external API calls or uploads."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import visual_guard as guard


def decision(approved=True, number=1):
    return {"number": number, "approved": approved, "frames": [approved] * 3,
            "visible_subject": "ice cubes in a glass",
            "evidence": "ice cubes float inside the visible drinking glass",
            "reason": "same object and action" if approved else "sea ice is not an ice cube in a drink"}


class VisualGuardTests(unittest.TestCase):
    def test_ambiguous_verdicts_cannot_pass(self):
        self.assertTrue(guard.verdict(decision(), 1)[0])
        for change in ({"visible_subject": ""}, {"frames": [True, True, False]},
                       {"number": True}, {"evidence": "vague"}, {"reason": ""}):
            self.assertFalse(guard.verdict({**decision(), **change}, 1)[0])

    def test_prior_narration_reaches_vision_model(self):
        captured = {}
        def fake_post(url, **kwargs):
            captured["parts"] = kwargs["json"]["contents"][0]["parts"]
            return Mock(raise_for_status=lambda: None, json=lambda: {
                "candidates": [{"content": {"parts": [{"text": json.dumps({"scenes": [decision()]})}]}}]})
        plan = {"topic": "why ice floats in water",
                "previous_narration": "Drop an ice cube into your drink.",
                "scenes": [{"voiceover": "It floats at the top."}]}
        with patch.dict("os.environ", {"GEMINI_API_KEY": "mock-value"}), patch.object(guard.requests, "post", fake_post):
            self.assertTrue(guard._model_review(plan, [[b"a", b"b", b"c"]])[0]["approved"])
        text = " ".join(part["text"] for part in captured["parts"] if "text" in part)
        self.assertIn("Drop an ice cube into your drink", text)
        self.assertIn("It floats at the top", text)
        self.assertIn("sea-ice field", text)
        self.assertEqual(sum("inline_data" in part for part in captured["parts"]), 3)

    def test_candidate_uses_scene_duration_and_referent(self):
        first = {"voiceover": "Drop an ice cube into your drink."}
        second = {"voiceover": "It floats at the top."}
        plan = {"topic": "ice floating", "scenes": [first, second], "scene_durations": [5., 7.2]}
        captured = {}
        def sample(source, work, prefix, duration=None):
            captured["duration"] = duration
            return [b"a", b"b", b"c"]
        def model(one_scene, previews):
            captured["previous"] = one_scene["previous_narration"]
            return [decision()]
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(sys.modules, {"upgrade": types.SimpleNamespace(CURRENT_PLAN=plan)}), \
                 patch.object(guard, "sample_frames", sample), patch.object(guard, "_model_review", model):
                self.assertTrue(guard.review_candidate(second, Path(directory) / "source.mp4", Path(directory), 1)[0])
        self.assertEqual(captured, {"duration": 7.2, "previous": first["voiceover"]})

    def test_final_mismatch_blocks_upload_and_checks_rendered_clip(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            movie = directory / "short.mp4"
            movie.write_bytes(b"test")
            (directory / "clip_00.mp4").write_bytes(b"rendered")
            plan = {"topic": "ice cubes", "scenes": [{"voiceover": "An ice cube floats.",
                    "pexels_video_id": 123}]}
            with patch.object(guard, "sample_frames", return_value=[b"a", b"b", b"c"]) as frames, \
                 patch.object(guard, "_model_review", return_value=[decision(False)]):
                with self.assertRaisesRegex(ValueError, "upload cancelled"):
                    guard.check(plan, directory, movie)
            self.assertEqual(frames.call_args.args[0].name, "clip_00.mp4")
            self.assertFalse(json.loads((directory / "plan.json").read_text())["visual_review"]["approved"])

    def test_preview_crop_matches_playback_and_wraps_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "source.mp4"
            source.write_bytes(b"test")
            times = []
            def fake_run(command, **kwargs):
                times.append((float(command[command.index("-ss") + 1]), command[command.index("-vf") + 1]))
                Path(command[-1]).write_bytes(b"x" * 1200)
            with patch.object(guard, "_duration", return_value=4.0), patch.object(guard.subprocess, "run", fake_run):
                self.assertEqual(len(guard.sample_frames(source, directory, "sample", 7.0)), 3)
            for actual, expected in zip([x[0] for x in times], [1.26, 3.5, 1.74]):
                self.assertAlmostEqual(actual, expected, places=2)
            self.assertTrue(all("crop=360:640" in filt for _, filt in times))


if __name__ == "__main__":
    unittest.main()

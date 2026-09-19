"""Offline proof that failure recovery never silently approves an invalid video."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import quality_entry
import resilient_plan_guard
import selection_guard
import stock_recovery
import upgrade


class RecoveryTests(unittest.TestCase):
    def test_malformed_json_is_retried_then_valid_json_returned(self):
        calls = []

        def fake_model(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                upgrade.bot.die("Gemini produced invalid structured output: JSONDecodeError")
            return {"approved": True, "issues": []}

        with patch.object(quality_entry, "_original_model_json", fake_model), \
             patch.object(resilient_plan_guard.time, "sleep"):
            resilient_plan_guard._installed = False
            resilient_plan_guard.install()
            self.assertEqual(quality_entry._original_model_json("review"), {"approved": True, "issues": []})
            self.assertEqual(len(calls), 2)
            self.assertIn("JSON FORMAT RETRY", calls[1])
        resilient_plan_guard._installed = False

    def test_no_matching_footage_checks_second_page_without_skipping_review(self):
        pages = []

        def original_get(url, *args, **kwargs):
            pages.append(kwargs["params"]["page"])
            return object()

        def fake_choose(scene, index):
            from requests import get
            get("https://api.pexels.com/v1/videos/search", params={"page": 1})
            if pages[-1] == 1:
                upgrade.bot.die(f"No matching footage for scene {index + 1} after 9 candidates; upload cancelled.")
            return Path("verified-scene.mp4")

        with patch.object(selection_guard, "choose", fake_choose), \
             patch.object(stock_recovery.requests, "get", original_get):
            stock_recovery._installed = False
            stock_recovery.install()
            self.assertEqual(quality_entry.upgrade.matched_pexels_video({}, 0), Path("verified-scene.mp4"))
            self.assertEqual(pages, [1, 2])
        stock_recovery._installed = False


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Offline regression checks for Shorts metadata, Full HD sources and idempotency."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import creator_guard as guard
import hd_footage_guard


class CreatorGuardTests(unittest.TestCase):
    def plan(self):
        return {
            "title": "Why Ice Cubes Crack? #Shorts",
            "description": "Cold ice cracks when it warms. Listen to the sound. #Shorts | Everyday Mysteries.",
            "topic": "why ice cubes crack",
            "theme": "everyday",
            "narration": "Why do ice cubes crack inside a glass of water?",
        }

    def test_metadata_is_short_specific_and_hashtag_free(self):
        plan = self.plan()
        guard.metadata(plan)
        self.assertEqual(plan["title"], "Why Ice Cubes Crack")
        self.assertNotIn("#", plan["description"])
        self.assertNotIn("Everyday Mysteries", plan["description"])
        self.assertTrue(3 <= len(plan["tags"]) <= 8)
        self.assertTrue(all(tag not in {"shorts", "ai", "viral"} for tag in plan["tags"]))

    def test_ai_tool_advertisement_removed_from_description(self):
        plan = self.plan()
        plan["description"] = "Watch ice cubes crack. Made with Gemini AI. #Shorts"
        guard.metadata(plan)
        self.assertEqual(plan["description"], "Watch ice cubes crack.")

    def test_same_topic_cannot_be_reserved_twice(self):
        plan = self.plan()
        guard.metadata(plan)
        records = []
        with patch.object(guard, "_history", return_value=(records, None, "mock", {})), \
             patch.object(guard, "_store"):
            guard._reserve(plan)
            self.assertEqual(len(records), 1)
            with self.assertRaisesRegex(ValueError, "duplicate Shorts"):
                guard._reserve(plan)

    def test_no_history_credentials_blocks_upload(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "credentials unavailable"):
                guard._credentials()

    def test_invalid_title_is_rejected(self):
        plan = self.plan()
        plan["title"] = "A" * 70
        with self.assertRaisesRegex(ValueError, "8-52"):
            guard.metadata(plan)

    def test_only_full_hd_and_higher_source_accepted(self):
        clips = {"video_files": [
            {"width": 360, "height": 720, "link": "https://example.com/poor.mp4"},
            {"width": 1080, "height": 1920, "link": "https://example.com/fhd.mp4"},
            {"width": 720, "height": 1280, "link": "https://example.com/hd.mp4"},
            {"width": 2160, "height": 3840, "link": "https://example.com/4k.mp4"},
        ]}
        result = hd_footage_guard.hd_file_options(clips)
        self.assertEqual(result, ["https://example.com/fhd.mp4", "https://example.com/4k.mp4"])
        self.assertNotIn("https://example.com/poor.mp4", result)
        self.assertNotIn("https://example.com/hd.mp4", result)

    def test_low_resolution_only_has_no_fallback(self):
        clips = {"video_files": [
            {"width": 720, "height": 1280, "link": "https://example.com/hd.mp4"},
            {"width": 1080, "height": 1080, "link": "https://example.com/square.mp4"},
        ]}
        self.assertEqual(hd_footage_guard.hd_file_options(clips), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

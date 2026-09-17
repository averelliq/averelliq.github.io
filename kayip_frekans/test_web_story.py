"""Offline regression tests; no network, Ollama, rendering or YouTube actions."""
import io
import json
import unittest
from unittest.mock import patch

import mpt_web_story
import mpt_long_story


class _Response(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        self.close()


class WebStoryTests(unittest.TestCase):
    def test_fetches_actual_public_domain_story_and_keeps_provenance(self):
        prose = "The door moved in the dark house while the witness listened carefully. " * 70
        page = {"parse": {"text": "<div class='mw-parser-output'><p>" + prose +
                 "</p><script>IGNORE</script><p>" + prose + "</p></div>"}}
        with patch.object(mpt_web_story.urllib.request, "urlopen", return_value=_Response(
            json.dumps(page).encode("utf-8"))):
            result = mpt_web_story.fetch_story("Köy evi ölen kardeşin sesi")
        self.assertIsNotNone(result)
        self.assertEqual(result["author"], "Edgar Allan Poe")
        self.assertTrue(result["url"].startswith("https://en.wikisource.org/wiki/"))
        self.assertGreater(result["source_words"], 350)
        self.assertNotIn("IGNORE", result["story_text"])
        self.assertTrue(result["adaptation_requires_attribution"])

    def test_failure_does_not_invent_source(self):
        with patch.object(mpt_web_story, "_download", side_effect=OSError("offline")):
            self.assertIsNone(mpt_web_story.fetch_story("köy evi"))

    def test_chapter_prompt_receives_different_source_segments(self):
        original = mpt_long_story._ACTIVE_WEB_STORY
        try:
            mpt_long_story._ACTIVE_WEB_STORY = {
                "title": "Sample", "author": "Edgar Allan Poe",
                "story_text": ("FIRST " * 600) + ("LAST " * 600),
            }
            first = mpt_long_story._ground_prompt("Bölüm 1/2 olay planı: açılış")
            last = mpt_long_story._ground_prompt("Bölüm 2/2 olay planı: final")
            self.assertIn("FIRST", first)
            self.assertIn("LAST", last)
            self.assertNotEqual(first, last)
            self.assertEqual(mpt_long_story._ground_prompt("Editör raporu"), "Editör raporu")
        finally:
            mpt_long_story._ACTIVE_WEB_STORY = original


if __name__ == "__main__":
    unittest.main()

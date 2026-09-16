"""Offline regression tests. These NEVER call Google APIs or upload videos."""
from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

import trend_ideas as trends


class TrendCredentialsTests(unittest.TestCase):
    def setUp(self) -> None:
        trends._CACHE.clear()
        trends._REFERENCES.clear()

    def test_missing_key_never_uses_upload_oauth_or_network(self) -> None:
        with patch.dict(os.environ, {"YT_DATA_API_KEY": "", "YT_CLIENT_ID": "old",
                                   "YT_CLIENT_SECRET": "old", "YT_REFRESH_TOKEN": "old",
                                   "SHORTS_TREND_MODE": "auto"}), \
             patch.object(trends.requests, "get", side_effect=AssertionError("Network attempted")), \
             patch.object(trends.requests, "post", side_effect=AssertionError("OAuth attempted")):
            self.assertEqual(trends.pick_topic("science", lambda theme: "original science topic", lambda prompt: {}),
                             "original science topic")
            self.assertIsNone(trends.reference_for("science"))
            with self.assertRaisesRegex(trends.TrendAccessError, "YT_DATA_API_KEY missing"):
                trends._credentials()

    def test_valid_key_stays_separate_from_gemini_and_oauth(self) -> None:
        with patch.dict(os.environ, {"YT_DATA_API_KEY": "TEST_ONLY_DATA_KEY", "GEMINI_API_KEY": "NOT_DATA_KEY",
                                   "YT_REFRESH_TOKEN": "NOT_A_SEARCH_TOKEN"}), \
             patch.object(trends.requests, "post", side_effect=AssertionError("OAuth attempted")):
            self.assertEqual(trends._credentials(), ({}, {"key": "TEST_ONLY_DATA_KEY"}))

    def test_403_reports_reason_without_leaking_key(self) -> None:
        response = Mock(ok=False, status_code=403)
        response.json.return_value = {"error": {"errors": [{"reason": "insufficientPermissions"}]}}
        with self.assertRaises(trends.TrendAccessError) as caught:
            trends._response_json(response)
        self.assertIn("HTTP 403", str(caught.exception))
        self.assertIn("insufficientPermissions", str(caught.exception))
        self.assertNotIn("TEST_ONLY_DATA_KEY", str(caught.exception))

    def test_quota_error_reports_reason_without_response_url(self) -> None:
        response = Mock(ok=False, status_code=403)
        response.json.return_value = {"error": {"errors": [{"reason": "quotaExceeded"}]}}
        response.url = "https://www.googleapis.com/youtube/v3/search?key=SHOULD_NEVER_PRINT"
        with self.assertRaises(trends.TrendAccessError) as caught:
            trends._response_json(response)
        self.assertIn("quotaExceeded", str(caught.exception))
        self.assertNotIn("SHOULD_NEVER_PRINT", str(caught.exception))

    def test_trend_off_ignores_available_key(self) -> None:
        with patch.dict(os.environ, {"YT_DATA_API_KEY": "TEST_ONLY_DATA_KEY", "SHORTS_TREND_MODE": "off"}), \
             patch.object(trends.requests, "get", side_effect=AssertionError("Network attempted")):
            self.assertEqual(trends.pick_topic("history", lambda theme: "original history topic", lambda prompt: {}),
                             "original history topic")


if __name__ == "__main__":
    unittest.main()

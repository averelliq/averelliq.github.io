import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import shorts_bot
from content_rules import validate_content_spec

class BotTests(unittest.TestCase):
    def test_template_plan_is_rejected_until_sources_are_verified(self):
        plan = json.loads((ROOT / "examples" / "restoration_plan.json").read_text())
        self.assertEqual(shorts_bot.validate_plan(plan), [])
        self.assertEqual(plan["duration"], 40.0)
        self.assertEqual(plan["cta"]["text"], "LIKE + SUBSCRIBE")

    def test_manufacturing_spec_is_allowed(self):
        spec = json.loads((ROOT / "examples" / "ai_manufacturing_spec.json").read_text())
        self.assertEqual(validate_content_spec(spec["content_spec"]), [])

    def test_random_content_is_rejected(self):
        spec = {"category":"metalworking", "title":"Oddly satisfying espresso foam", "description":"A random clip", "original_ai_scenes":True, "realistic_ai":True, "ai_disclosure":True}
        self.assertTrue(validate_content_spec(spec))

if __name__ == "__main__":
    unittest.main()

"""Gemini-independent previews for three explicitly requested CurioRush subjects.

NOT an automatic uploader. Seven source-linked clips, early/middle/late frames,
actual rendered MP4 and human audiovisual review are required before release.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pottery_preview_entry as preview
import quality_entry
import upgrade

CONFIG = {
    "glass": {
        "topic": "how glassblowers shape hot glass",
        "title": "How Hot Glass Takes Shape",
        "description": "Watch glassblowers transform hot glass with careful hands and tools.",
        "tags": ["glassblowing", "craft", "glass making"],
        "queries": ["glassblower shaping hot glass", "glass blowing workshop closeup", "glass blowing furnace workshop", "glassblower working molten glass", "glass blowing artist", "glassblower blowing glass", "glass blowing glass art", "glass blowing pipe", "glassblowing close up", "glass blowing craft"],
        "speech": [
            "Watch how a glassblower works with glowing, hot glass.",
            "The material is gathered and kept hot enough to shape.",
            "Careful movements help the glass change form while it is soft.",
            "The maker turns the piece and checks its shape as they work.",
            "Tools and practiced hands help guide the changing surface.",
            "The glass must be handled carefully as it starts to cool.",
            "Each step depends on controlling heat and the shape of the glass.",
        ],
        "captions": ["Hot glass", "The workshop", "Watch it change", "Turning and shaping", "Careful hands", "Heat matters", "Glassblowing"],
    },
    "typewriter": {
        "topic": "how an old typewriter types letters",
        "title": "Inside a Typewriter",
        "description": "A closer look at the moving parts of a classic typewriter.",
        "tags": ["typewriter", "mechanism", "how it works"],
        "queries": ["mechanical typewriter typing close up", "vintage typewriter keys moving", "typewriter typing letters", "typewriter mechanism closeup", "antique typewriter working", "typewriter keys fingers", "manual typewriter typing", "typewriter paper typing", "old typewriter close up", "vintage typewriter working"],
        "speech": [
            "What happens when someone presses a key on this old typewriter?",
            "Each key sets a small mechanical linkage into motion.",
            "The moving mechanism brings a letter toward the paper.",
            "An inked ribbon transfers the character onto the page.",
            "The machine moves its typing position to make room for the next letter.",
            "Press another key, and the mechanical sequence starts again.",
            "That's how a typewriter turns simple key presses into printed words.",
        ],
        "captions": ["Press a key", "The linkage", "Letter meets paper", "An inked ribbon", "Next position", "Another letter", "Printed words"],
    },
    "grapes": {
        "topic": "how grapes become fresh juice",
        "title": "Grapes to Juice",
        "description": "Follow grapes as they are pressed into fresh juice.",
        "tags": ["grape juice", "fruit", "food making"],
        "queries": ["fresh grapes grape juice making", "grapes juice press", "grape juice squeezing grapes", "fresh grape juice pouring", "grape juice preparation", "grapes crushing juice", "grapes in juicer", "grape pressing fresh juice", "fresh grape juice glass", "grapes juicing closeup"],
        "speech": [
            "How does a bunch of grapes become a glass of juice?",
            "First, the fruit is prepared for pressing.",
            "Pressure breaks the grape skins and releases the liquid inside.",
            "The juice flows out while the solids are left behind.",
            "A strainer can separate bits of skin and pulp.",
            "The fresh liquid is collected and poured into a glass.",
            "From whole grapes to juice, it is the fruit's liquid being released.",
        ],
        "captions": ["From grapes", "Prepare the fruit", "Pressing", "Juice released", "Separate solids", "Pour the juice", "Grapes to juice"],
    },
}


def main() -> None:
    name = os.environ.get("SHORTS_BATCH_TOPIC", "")
    if name not in CONFIG:
        raise ValueError("Unknown requested preview subject")
    if os.environ.get("SHORTS_SKIP_UPLOAD") != "1":
        raise ValueError("Gemini-independent preview MUST NOT auto-publish")
    manifest = json.loads((Path(__file__).parent / "three_offline_request.json").read_text(encoding="utf-8"))
    if manifest.get("preview_only") is not True or manifest.get("topics") != list(CONFIG):
        raise ValueError("Missing matching preview-only instruction")
    config = CONFIG[name]
    if len(config["speech"]) != 7 or len(config["captions"]) != 7:
        raise ValueError("Expected seven distinct script scenes")
    preview.TOPIC = config["topic"]
    preview.SEARCHES = tuple(config["queries"])
    preview.SPEECH = tuple(config["speech"])
    preview.CAPTIONS = tuple(config["captions"])
    preview.MAX_CANDIDATES = 85
    preview.MAX_DOWNLOADS = 40
    upgrade.aligned_build_video = quality_entry._original_build
    print(f"OFFLINE PREVIEW {name}: Gemini quota bypass via direct licensed-source review; publishing OFF", flush=True)
    preview.main()
    out = upgrade.bot.OUT
    plan_path = out / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("topic") != config["topic"] or len(plan.get("scenes", [])) != 7:
        raise ValueError("Generated plan/subject mismatch")
    plan.update(title=config["title"], description=config["description"], tags=config["tags"],
                batch_topic=name, independent_final_vision_review="Manual review required before release")
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OFFLINE PREVIEW READY {name}: {config['title']}; 21 frames and exact MP4 require review", flush=True)


if __name__ == "__main__":
    main()

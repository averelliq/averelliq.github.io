"""CurioRush's three repeatable formats, installed without weakening the existing guards.

Internal schedule slots retain science/history/everyday identifiers for compatibility;
their editorial meanings are now HOW IT WORKS / HOW IT'S MADE / RAW TO FINISHED.
"""
from __future__ import annotations

import re

import footage_first
import quality_entry
import trend_ideas
import upgrade

FORMATS = {
    "science": ("HOW IT WORKS", (
        ("how a bicycle chain transfers pedal power", ("bicycle chain rotating closeup", "bicycle pedal chainring moving", "bike rear sprocket spinning", "bicycle drivetrain working", "bicycle chain gears", "cyclist pedaling bicycle")),
        ("how a fishing reel winds line", ("fishing reel mechanism", "fishing reel spinning closeup", "fishing reel turning", "fishing reel winding line")),
        ("how an old typewriter types letters", ("typewriter keys mechanism", "vintage typewriter typing", "typewriter close up", "mechanical typewriter working")),
    )),
    "history": ("HOW IT'S MADE", (
        ("how a pizza is made", ("pizza dough stretching", "pizza chef preparing", "pizza toppings preparation", "pizza baking oven", "pizza making closeup", "fresh pizza slicing")),
        ("how glassblowers shape hot glass", ("glass blowing workshop", "glassblower shaping glass", "glass blowing closeup", "glass blowing furnace")),
        ("how a carpenter makes wooden furniture", ("carpenter woodworking workshop", "wood sanding closeup", "wood cutting carpenter", "wood furniture making")),
    )),
    "everyday": ("RAW TO FINISHED", (
        ("how whole oranges become fresh juice", ("fresh oranges closeup", "orange cutting hands", "orange juicer squeezing", "fresh orange juice pouring", "orange juice making", "glass of fresh orange juice")),
        ("how cocoa becomes chocolate", ("cocoa beans processing", "chocolate melting making", "chocolate molds pouring", "chocolate factory production")),
        ("how grapes become fresh juice", ("fresh grapes harvesting", "grapes crushing juice", "grape juice pouring", "fresh grape juice making")),
    )),
}

_installed = False


def install() -> None:
    global _installed
    if _installed:
        return
    for slot, (_, candidates) in FORMATS.items():
        footage_first.BANK[slot] = candidates
        upgrade.TOPICS[slot] = tuple(topic for topic, _ in candidates)
        for topic, queries in candidates:
            footage_first.SPECIAL[topic] = queries

    # Never import a trending subject from another format into this production.
    # The existing duplicate guard skips a published/reserved topic and tries
    # the next candidate. An exhausted category fails closed.
    footage_first._seed = lambda theme: FORMATS[theme][1][0][0]
    upgrade.choose_topic = lambda theme: trend_ideas._CACHE.get(theme, FORMATS[theme][1][0][0])
    trend_ideas._REFERENCES.clear()
    previous_model = quality_entry._original_model_json

    def process_story(prompt: str):
        if prompt.startswith("You are an English-language, original educational Shorts scriptwriter"):
            topic = next((topic for slot in FORMATS for topic, _ in FORMATS[slot][1]
                          if topic in prompt), None)
            slot = next((slot for slot in FORMATS if topic in upgrade.TOPICS[slot]), None)
            if not slot:
                raise ValueError("Process Short has no approved category or topic")
            label = FORMATS[slot][0]
            prompt += ("\nCURiORUSH THREE-FORMAT EDITORIAL RULES. FORMAT: " + label + ". "
                "This is ONE physical process or mechanism, not a list of facts. "
                "For HOW IT'S MADE: show a real starting material, genuinely visible "
                "making steps in their physical order, then a finished item ONLY if "
                "the approved footage actually shows it. "
                "For HOW IT WORKS: follow energy or movement through the SAME visible "
                "mechanism; distinguish directly visible parts from hidden mechanisms. "
                "For RAW TO FINISHED: follow the SAME material through real, ordered "
                "transformations, and never imply a step was filmed when absent. "
                "Start with the most visually gripping action in approved clip 1, "
                "explain what the viewer can actually SEE, and deliver a clear answer "
                "by the end. Refer to each numbered approved clip's specific action "
                "rather than claiming imagined stages or invisible science are visible. "
                "If clips do not cover a complete process, accurately describe ONLY "
                "the available portion; do not fabricate a finished reveal. "
                "Write fresh natural English, 75-90 total spoken words, eight distinct "
                "shots, 1-6-word readable captions and no repetitive generic CTA. "
                "Avoid misinformation about manufacturing (forged metal is heated "
                "and hammered, not necessarily melted). "
                "Choose a truthful short title (8-45 characters) and an original, "
                "specific one-sentence description (at most 120 characters). "
                "No hashtags, AI tool names, reused creator video, or irrelevant stock.")
        return previous_model(prompt)

    quality_entry._original_model_json = process_story
    _installed = True
    print("CURiORUSH FORMATS: made / mechanism / raw-to-finished installed; all safety checks intact", flush=True)

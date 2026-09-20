"""CurioRush three process formats: film-first, truthful, non-repeating subjects.

Keep legacy science/history/everyday slot identifiers for schedule compatibility.
"""
from __future__ import annotations

import footage_first
import quality_entry
import trend_ideas
import upgrade

FORMATS = {
    "science": ("HOW IT WORKS", (
        ("how an old typewriter types letters", ("vintage typewriter typing", "typewriter keys moving", "mechanical typewriter working", "typewriter paper typing", "typewriter typebars closeup", "old typewriter close up", "typewriter mechanism", "person typing typewriter", "typewriter carriage moving")),
        ("how a fishing reel winds line", ("fishing reel mechanism", "fishing reel spinning closeup", "fishing reel turning", "fishing reel winding line", "fisherman winding fishing reel")),
        ("how a music box plays a tune", ("music box mechanism", "music box playing", "music box closeup", "music box turning")),
    )),
    "history": ("HOW IT'S MADE", (
        ("how glassblowers shape hot glass", ("glass blowing workshop", "glassblower shaping glass", "glass blowing closeup", "glass blowing furnace", "hot glass artist", "hand blown glass", "glassblower making vase", "glass blowing molten glass", "glass working studio")),
        ("how a chef makes handmade pasta", ("fresh pasta making", "pasta dough rolling", "chef making pasta", "handmade pasta cutting", "pasta making close up")),
        ("how a carpenter makes wooden furniture", ("carpenter woodworking workshop", "wood sanding closeup", "wood cutting carpenter", "wood furniture making")),
        ("how a steel gear is made", ("metal gear manufacturing", "steel gear machining", "gear cutting machine", "industrial gear production", "metal gear cnc cutting", "gear hobbing machine", "gear teeth milling", "machined metal gears", "gear factory machinery", "metal gear inspection", "industrial machine gears", "gear machining closeup")),
    )),
    "everyday": ("RAW TO FINISHED", (
        ("how grapes become fresh juice", ("fresh grapes harvesting", "washing fresh grapes", "grapes pressing juice", "grapes crushing juice", "fresh grape juice pouring", "grape juice making", "grapes juicing", "grape juice glass", "grape processing")),
        ("how lemons become lemonade", ("fresh lemons cutting", "lemon squeezing juice", "making fresh lemonade", "lemon juice pouring", "homemade lemonade preparing")),
        ("how cocoa becomes chocolate", ("cocoa beans processing", "chocolate melting making", "chocolate molds pouring", "chocolate factory production")),
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
            prompt += ("\nCURiORUSH EDITORIAL FORMAT: " + FORMATS[slot][0] + ". "
                "Follow one physical object or process, not a list of unrelated facts. "
                "HOW IT'S MADE: real making actions in physically truthful order. "
                "HOW IT WORKS: follow energy/movement through the SAME visible mechanism; "
                "never claim invisible mechanisms are shown by unrelated footage. "
                "RAW TO FINISHED: follow the SAME material in ordered transformations. "
                "Use only actual actions described by approved numbered footage; do not "
                "invent an unfilmed stage or finished reveal. Start on visible action. "
                "Eight distinct shots, fresh natural English, 75-90 total spoken words, "
                "clear accurate answer, readable 1-6-word captions; no generic CTA. "
                "Do not mistake heating/forging for melting. Use original concise "
                "truthful title 8-45 characters, one-sentence specific description "
                "under 120 characters. No hashtags, AI-tool names or irrelevant clips.")
        return previous_model(prompt)

    quality_entry._original_model_json = process_story
    _installed = True
    print("CURIORUSH FORMATS: three fresh subjects installed; original quality checks retained", flush=True)

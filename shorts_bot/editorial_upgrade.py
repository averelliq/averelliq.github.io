"""Original, broad-appeal curiosity editorial layer for the scheduled cloud bot.

YouTube trend videos are used ONLY for public metadata and the underlying topic.
Never download/reuse a third party's video, voice, script, thumbnail or scene order.
The established source-footage, voice and final-review publishing gates remain.
"""
from __future__ import annotations

import json
import os
import re

import trend_ideas
import upgrade

IDENTITY = "Everyday mysteries explained in 30 seconds."
SERIES = "Everyday Mysteries"
CTA = "One new mystery every day. Subscribe for more."

EXTRA_TOPICS = {
    "science": (
        "why lightning produces thunder", "how an octopus changes texture",
        "why a rainbow is curved", "why flamingos become pink",
        "how ants navigate without maps", "why a jellyfish glows",
        "how a dolphin uses echolocation", "why Saturn has rings",
        "why the Moon has phases", "how a butterfly tastes with feet",
        "why a chameleon changes color", "how a hummingbird flies backward",
        "what makes a volcano erupt", "why some beaches glow at night",
        "how a spider senses movement", "why a meteor glows",
        "how a bee communicates with dancing", "why the ocean looks blue",
        "how a lizard regrows its tail", "why Venus has a long day",
    ),
    "history": (
        "why ancient Romans used concrete", "how ancient Egyptians moved stone",
        "why old castles had spiral staircases", "how the first cameras worked",
        "why ancient ships used stars", "how a mechanical clock keeps time",
        "how a typewriter moves letters", "why medieval bridges had houses",
        "how the first telephone carried voices", "why lighthouses flash in patterns",
        "how the first bicycle was balanced", "how old elevators stayed safe",
        "why ancient roads lasted so long", "how the first submarine moved",
        "how early maps showed the world", "how the compass points north",
        "why ancient buildings had courtyards", "how early film created motion",
        "how the first traffic lights worked", "how a steam engine moves",
    ),
    "everyday": (
        "why soda bubbles rise", "why onions make eyes water",
        "why a cold glass gets wet outside", "why coffee stains a cup",
        "why ice cubes crack in water", "why bread turns brown",
        "why a phone screen responds to touch", "why an elevator makes ears pop",
        "why toothpaste foams", "why a microwave heats food",
        "why fingerprints leave marks", "why a door creaks",
        "why a rubber band snaps back", "why a straw looks bent in water",
        "why metal feels colder than wood", "why soap breaks down grease",
        "why a zipper stays closed", "why raindrops cling to windows",
        "why a balloon sticks to a wall", "why your reflection looks reversed",
        "why a candle flame flickers", "why salt makes ice melt",
    ),
}

POLICY = """
CHANNEL BRAND: Everyday mysteries explained in 30 seconds. Broad English-language curiosity: nature, animals, space, psychology/perception, technology, history, everyday objects, and surprising but verifiable science.
Aim for 25-35 seconds and 65-80 words, with the opening observation/action in the FIRST 2 SECONDS. No logo, greetings, introductions or generic setup. Show the precise promised subject immediately and match EACH next visual to its sentence; prefer filmed real-world shots, never vector art, slideshow, AI illustrations, fake demonstrations, or generic filler. Keep changes every 3-5 seconds when usable distinct footage exists. Exactly ONE main question, a true satisfying explanation, and a natural one-line CTA only AFTER the answer, near the end: 'One new mystery every day. Subscribe for more.' Do not invent a numerical series episode. Identify the format in description as 'Everyday Mysteries'.
Originality: you MAY take the abstract educational topic from recent YouTube metadata, but NEVER reproduce a video's title, script, footage, audio, thumbnail, distinctive creative presentation, or scene order. Write fresh original narration. A popular video title is NOT scientific evidence; reject unverified, misleading or sensational claims. For unavailable footage, the existing fail-closed video gate must cancel publication. Return exactly the JSON shape already requested.
"""

_installed = False


def install() -> None:
    global _installed
    if _installed:
        return
    previous_choose = upgrade.choose_topic
    previous_model = upgrade.model_json
    previous_validate = upgrade.validate_plan
    upgrade.TOPICS = {theme: tuple(dict.fromkeys((*upgrade.TOPICS[theme], *EXTRA_TOPICS[theme])))
                      for theme in upgrade.THEMES}

    def choose(theme: str) -> str:
        return trend_ideas.pick_topic(theme, previous_choose, previous_model)

    def model(prompt: str):
        if prompt.startswith("You are an English-language, original educational Shorts scriptwriter"):
            prompt = POLICY + "\n" + prompt
        return previous_model(prompt)

    def validate(plan, theme):
        result = previous_validate(plan, theme)
        words = len(result["narration"].split())
        # Reject overly long output rather than silently speeding up narration.
        if words > 90:
            raise ValueError("Short exceeds 90 spoken words; rewrite for 25-35 seconds")
        opening = re.split(r"[.!?]", result["scenes"][0]["voiceover"], 1)[0]
        if len(opening.split()) > 10:
            raise ValueError("Start with a concise first-two-second curiosity hook")
        if not re.search(r"subscribe for more|subscribe for (?:daily|new) (?:mysteries|facts)",
                         result["scenes"][-1]["voiceover"], re.I):
            raise ValueError("After the reveal, end with one natural subscription call")
        description = result["description"]
        if SERIES.lower() not in description.lower():
            description = description.rstrip() + " | Everyday Mysteries."
        if len(description) > 400:
            raise ValueError("Description too long for series label")
        result["description"] = description
        result["channel_identity"] = IDENTITY
        result["series"] = SERIES
        ref = trend_ideas.reference_for(theme)
        if ref:
            result["trend_reference"] = ref
            result["trend_reference_not_reused"] = True
        return result

    upgrade.choose_topic = choose
    upgrade.model_json = model
    upgrade.validate_plan = validate
    _installed = True

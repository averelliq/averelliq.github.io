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
CHANNEL BRAND: Everyday mysteries explained in 30 seconds. Broad English-language curiosity: nature, animals, space, technology, history, everyday objects, and surprising but verifiable science.
Write EXACTLY EIGHT scenes with 9-11 natural spoken words in EACH scene (72-88 words overall). The first sentence of the first scene must be a concrete, surprising, 7-9-word sentence ending in a period or question mark, with no introduction; show that observation in the first two seconds. Each following scene progresses logically toward one truthful explanation and matches available real-world footage. Give every scene one distinct 2-5-word Pexels search query and exactly two 2-5-word backup queries showing THAT SAME TOPIC; no fake demonstrations, generic filler, vector art, slide shows, AI illustrations or borrowed footage. Avoid invisible internal anatomy, microscopic processes and unfilmable historic recreations; describe the process while showing a visibly related real-world subject instead of pretending footage directly depicts an invisible process.
Exactly ONE main question, a satisfying true explanation and a short natural subscription invitation ONLY AFTER the answer in the last scene, such as 'Subscribe for more.' Preserve the precise video subject through every scene. No unrelated example objects or separate topics. Title includes #Shorts; description includes 'Everyday Mysteries'. Do not invent numerical episodes, unsupported facts or statistics. An original educational topic may come from public trending-video metadata, but never reproduce another video's title, script, footage, audio, thumbnail, distinctive presentation or scene order. A trending title is NOT scientific evidence. The existing fail-closed visual gate must cancel publication if suitable filmed footage cannot be found. Return exactly the JSON shape already requested.
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
    # quality_entry imported before install() caches the *unwrapped* model.
    # Its plan retries must call the editorial wrapper rather than silently
    # bypassing the detailed brief. Preserve the original review and QC gates.
    import quality_entry
    quality_entry._original_model_json = model
    _installed = True

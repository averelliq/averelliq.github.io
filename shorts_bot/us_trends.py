"""US-oriented, original educational topic selection for the global Shorts bot.

Google Trends US represents US *search interest*, not verified Shorts views.
YouTube Data API regionCode=US is US-directed discovery; video view totals
are global, not a measurement of US viewers. Never call either a guarantee.
Only the abstract, independently explainable subject is used: no source video,
script, voice, images, thumbnail, hook, scene order or other creative expression.
"""
from __future__ import annotations

import hashlib
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Callable

import requests

import trend_ideas

US_TRENDS_RSS = "https://trends.google.com/trending/rss?geo=US"
US_TRENDS_PAGE = "https://trends.google.com/trending?geo=US"
EASTERN = ZoneInfo("America/New_York")

# Subjects should be recognizable in the US and physically filmable. Historical
# explanations must be supported by documented facts in the script, not myths.
US_FALLBACKS: dict[str, tuple[str, ...]] = {
    "science": (
        "why a baseball curves in flight",
        "why a football spirals through the air",
        "why fireflies flash at night",
        "why a basketball bounces",
        "how a skateboard turns when tilted",
        "why lightning is seen before thunder",
        "how a tornado forms inside a thunderstorm",
        "why autumn leaves change color",
        "why a rainbow makes a curved arc",
        "why a frisbee stays airborne",
    ),
    "history": (
        "how early traffic lights controlled intersections",
        "how mechanical parking meters kept time",
        "how old-fashioned film cameras captured images",
        "how mechanical typewriters printed letters",
        "how vintage neon signs made light",
        "how early bicycles used pedal power",
        "how steam locomotives turned heat into motion",
        "why old lighthouses used rotating lenses",
        "how early telephones carried voices",
        "how traditional water wheels powered mills",
    ),
    "everyday": (
        "why microwave popcorn pops",
        "why soda bubbles rise in a glass",
        "why a takeaway coffee cup needs a sleeve",
        "why ice cream melts on a hot day",
        "why a car windshield fogs up",
        "why bread turns golden in a toaster",
        "why sneakers squeak on a clean floor",
        "why a zipper stays shut",
        "why soap removes grease from dishes",
        "why a cold drink gets wet on the outside",
    ),
}

# Exclude sensitive or ephemeral breaking-news claims. A sports headline about
# a game is not itself a science/education topic. Reject rather than copy.
BLOCKED = re.compile(
    r"(?i)\b(?:vs\.?|scores?|highlights?|injur(?:y|ies)|trades?|playoffs?|"
    r"election|senate|congress|president|politics?|trump|biden|war|shooting|"
    r"killed|death|died|attack|arrest|lawsuit|trial|outbreak|disease|"
    r"diagnos(?:is|ed)|cure|medication|stock market|cryptocurrency|"
    r"lottery|betting|gambling|scandal|rumou?r|leak|trailer|album)\b"
)
SAFE_THEME = {
    "science": re.compile(
        r"(?i)\b(?:science|space|nasa|moon|mars|meteor|comet|eclipse|aurora|"
        r"planet|rocket|animal|wildlife|cat|cats|dog|dogs|bird|birds|"
        r"whale|shark|bee|bees|butterfly|firefly|fireflies|cicada|"
        r"thunder|lightning|rainbow|tornado|volcano|ocean|dinosaur|"
        r"sun|saturn|nature|fossil|baseball|football|basketball|skateboard)\b"
    ),
    "history": re.compile(
        r"(?i)\b(?:history|historical|historic|museum|ancient|archaeology|"
        r"archaeological|artifact|artifacts|invention|vintage|retro|"
        r"centennial|anniversary|heritage|apollo|space shuttle|"
        r"lighthouse|railroad|railway|steam engine)\b"
    ),
    "everyday": re.compile(
        r"(?i)\b(?:food|coffee|soda|popcorn|ice cream|bread|pizza|"
        r"burger|phone|iphone|battery|car|train|airplane|flight|"
        r"grocery|kitchen|chocolate|pumpkin|weather|rain|snow|"
        r"football|baseball|basketball|robot|technology|water|soap|"
        r"cooking|restaurant|ice|drink|drinks|cheese|cookie|cookies|"
        r"bicycle|bike|camera|sneakers|electricity|sunset|rainbow)\b"
    ),
}

_installed = False


def _evergreen(theme: str) -> str:
    topics = US_FALLBACKS[theme]
    day = datetime.now(EASTERN).date().toordinal()
    return topics[(day + {"science": 0, "history": 3, "everyday": 6}[theme]) % len(topics)]


def _us_search_terms(theme: str) -> list[str]:
    """Parse public US feed; do not use it as evidence for facts in narration."""
    response = requests.get(
        US_TRENDS_RSS,
        headers={"User-Agent": "Mozilla/5.0 (compatible; OriginalEducationalShorts/1.0)"},
        timeout=18,
    )
    response.raise_for_status()
    if len(response.content) > 2_000_000:
        raise ValueError("Unexpectedly large US trends response")
    root = ET.fromstring(response.content)
    if root.tag != "rss":
        raise ValueError("US trends did not return an RSS feed")
    titles: list[str] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        if (8 <= len(title) <= 100 and not BLOCKED.search(title)
                and SAFE_THEME[theme].search(title) and title not in titles):
            titles.append(title)
    # Rotate among a few eligible trends so all three daily Shorts do not reuse
    # the same first item. No candidate is declared viral without supporting data.
    seed = (os.getenv("GITHUB_RUN_ID") or datetime.now(EASTERN).strftime("%Y%m%d")) + theme
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    start = int.from_bytes(digest[:2], "big") % max(1, min(len(titles), 8))
    pool = titles[:8]
    return (pool[start:] + pool[:start])[:4]


def install() -> None:
    """Preserve existing trend, stock, narration and upload safeguards."""
    global _installed
    if _installed:
        return
    previous = trend_ideas.pick_topic
    # regionCode=US, relevanceLanguage=en and safeSearch=strict already exist in
    # the YouTube Data API request; these more specific queries fit our audience.
    trend_ideas.QUERIES.update({
        "science": "science curiosity nature space US shorts facts",
        "history": "American inventions technology history explained shorts",
        "everyday": "everyday science food life hacks explained US shorts",
    })

    def pick(theme: str, evergreen: Callable[[str], str],
             model_json: Callable[[str], dict[str, Any]]) -> str:
        fallback = lambda unused_theme: _evergreen(theme)
        if os.getenv("SHORTS_US_TRENDS", "1").strip() != "0":
            try:
                for phrase in _us_search_terms(theme):
                    topic = trend_ideas._neutral_topic(theme, phrase, model_json)
                    if topic:
                        trend_ideas._CACHE[theme] = topic
                        trend_ideas._REFERENCES[theme] = {
                            "source": "Google Trends: United States search interest",
                            "region": "US",
                            "source_url": US_TRENDS_PAGE,
                            "observed_search_query": phrase,
                            "inspired_topic": topic,
                            "usage": "Search interest / abstract topic only; not Shorts viewership",
                        }
                        print(f"US SEARCH TREND: {phrase!r} -> original topic {topic!r}", flush=True)
                        return topic
                print("US SEARCH TRENDS: no appropriate filmable educational subject.", flush=True)
            except (requests.RequestException, ET.ParseError, ValueError, KeyError,
                    IndexError, TypeError, SystemExit) as exc:
                print(f"US SEARCH TRENDS unavailable ({type(exc).__name__}); "
                      "checking US-directed YouTube metadata/evergreen.", flush=True)
        result = previous(theme, fallback, model_json)
        if trend_ideas.reference_for(theme) is None:
            print(f"US EVERGREEN: original, US-familiar {theme} topic: {result}", flush=True)
        return result

    trend_ideas.pick_topic = pick
    _installed = True

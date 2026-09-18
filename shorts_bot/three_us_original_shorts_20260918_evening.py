"""Three ORIGINAL US-interest Shorts; never reuse other creators' video, audio or script.

US relevance: phone technology, basketball physics and American pizza food science.
These are trend-inspired editorial themes, NOT claims of proven viral performance.
Preflight is upload-free. Each production job is a distinct one-shot invocation.
"""
from __future__ import annotations

import sys

import gemini_transient_guard
import two_original_shorts_20260918 as pair

CTA = pair.CTA
PLANS = {
    "phone": {
        "slug": "why_smartphones_have_multiple_camera_lenses_us_original",
        "topic": "why smartphones have several camera lenses",
        "theme": "science", "series": "Everyday Mysteries",
        "channel_identity": "Everyday mysteries explained in 30 seconds.",
        "title": "Why Does Your Phone Have THREE Cameras? #Shorts",
        "description": "Why do some smartphones have multiple rear cameras? Wide, ultra-wide and telephoto lenses provide different views. Original voiceover and independently checked filmed footage. Everyday Mysteries. Source: https://developer.apple.com/documentation/avfoundation/avcapturedevice/devicetype-swift.struct/builtintriplecamera #Shorts #Phone #Tech",
        "tags": ["shorts", "phone camera", "smartphone", "technology", "science", "everyday mysteries"],
        "scenes": [
            {"voiceover": "Your phone has three cameras. But they do not all see the same thing.",
             "query": "smartphone triple cameras", "backup_queries": ["smartphone rear cameras", "iphone camera lenses"], "caption": "Three different cameras"},
            {"voiceover": "The main camera gives a familiar view. Another lens can fit much more into one picture.",
             "query": "smartphone taking photo", "backup_queries": ["phone camera photography", "person taking phone photo"], "caption": "One view is wider"},
            {"voiceover": "An ultra-wide camera captures a bigger scene without making you step backward.",
             "query": "phone landscape photography", "backup_queries": ["smartphone photographing city", "mobile phone landscape"], "caption": "Capture a bigger scene"},
            {"voiceover": "A telephoto camera frames distant details more tightly. Some phones switch cameras as you zoom.",
             "query": "smartphone zoom camera", "backup_queries": ["phone camera closeup", "smartphone photography closeup"], "caption": "Different zoom views"},
            {"voiceover": "Those circles are different viewpoints, not extra decoration. One new mystery every day. Subscribe for more.",
             "query": "smartphone camera lenses", "backup_queries": ["mobile phone rear lenses", "triple camera smartphone"], "caption": "Each lens has a job"},
        ],
        "source_reading": ["https://developer.apple.com/documentation/avfoundation/avcapturedevice/devicetype-swift.struct/builtintriplecamera"],
        "trend_type": "Original US-focused phone technology subject; no verified per-video virality claim",
    },
    "basketball": {
        "slug": "why_basketballs_bounce_us_original",
        "topic": "why basketballs bounce and gradually lose height",
        "theme": "science", "series": "Everyday Mysteries",
        "channel_identity": "Everyday mysteries explained in 30 seconds.",
        "title": "Why Does a Basketball Bounce BACK? #Shorts",
        "description": "A basketball briefly squashes on impact, then its shell and compressed air spring back. Some energy becomes heat and sound. Original narration and verified filmed basketball scenes. Everyday Mysteries. Source: https://www.sciencebuddies.org/stem-activities/energetic-two-ball-bounces #Shorts #Basketball #Physics",
        "tags": ["shorts", "basketball", "sports science", "physics", "everyday mysteries"],
        "scenes": [
            {"voiceover": "That basketball bounces back. But where does its energy go?",
             "query": "basketball bouncing court", "backup_queries": ["basketball bouncing closeup", "basketball court dribble"], "caption": "Why does it bounce?"},
            {"voiceover": "As it falls, gravity makes the ball speed up toward the floor.",
             "query": "basketball bouncing floor", "backup_queries": ["basketball ground bounce", "basketball gym floor"], "caption": "Gravity pulls it down"},
            {"voiceover": "When it hits, its rubber shell briefly squashes and the trapped air compresses.",
             "query": "basketball slow motion", "backup_queries": ["basketball bounce slowmotion", "basketball bouncing close shot"], "caption": "The ball briefly squashes"},
            {"voiceover": "Then the shell and air spring back, pushing the ball upward. But not all energy returns.",
             "query": "basketball rebounding bounce", "backup_queries": ["basketball dribbling gym", "basketball bouncing court"], "caption": "It springs back up"},
            {"voiceover": "Some energy becomes heat and sound, so each bounce gets lower. One new mystery every day. Subscribe for more.",
             "query": "basketball bouncing repeatedly", "backup_queries": ["basketball dribbling closeup", "basketball bouncing gym"], "caption": "Each bounce gets lower"},
        ],
        "source_reading": ["https://www.sciencebuddies.org/stem-activities/energetic-two-ball-bounces"],
        "trend_type": "Original US-familiar sports physics subject; no verified per-video virality claim",
    },
    "pizza": {
        "slug": "why_mozzarella_pizza_cheese_stretches_us_original",
        "topic": "why mozzarella cheese stretches on hot pizza",
        "theme": "everyday", "series": "Everyday Mysteries",
        "channel_identity": "Everyday mysteries explained in 30 seconds.",
        "title": "Why Does PIZZA CHEESE Stretch So Far? #Shorts",
        "description": "Why does hot mozzarella stretch on pizza? Its milk-protein network and melt behavior help create those gooey strands. Original voiceover and filmed pizza shots. Everyday Mysteries. Source: https://agresearchmag.ars.usda.gov/2006/mar/foods/ #Shorts #Pizza #FoodScience",
        "tags": ["shorts", "pizza", "mozzarella", "cheese pull", "food science", "everyday mysteries"],
        "scenes": [
            {"voiceover": "Pull one pizza slice. Why does its cheese stretch so far?",
             "query": "pizza cheese pull", "backup_queries": ["stretchy pizza cheese", "pizza slice cheese stretch"], "caption": "Why does cheese stretch?"},
            {"voiceover": "Mozzarella contains a network of milk proteins called casein. That network helps hold the cheese together.",
             "query": "mozzarella pizza closeup", "backup_queries": ["pizza melted mozzarella", "stretchy mozzarella pizza"], "caption": "A network of proteins"},
            {"voiceover": "Heat softens the cheese. Its protein network can stretch into long strands instead of snapping immediately.",
             "query": "hot pizza cheese stretch", "backup_queries": ["melting pizza cheese", "pizza mozzarella strings"], "caption": "Heat makes it stretch"},
            {"voiceover": "That is the gooey cheese pull you see when a fresh slice leaves the pie.",
             "query": "lifting pizza slice", "backup_queries": ["pizza slice cheese pull", "pizza stringy cheese"], "caption": "The famous cheese pull"},
            {"voiceover": "As the pizza cools, the spectacular stretch changes. One new mystery every day. Subscribe for more.",
             "query": "pizza cheese strings", "backup_queries": ["pizza cheese closeup", "fresh pizza slice"], "caption": "Mozzarella makes the magic"},
        ],
        "source_reading": ["https://agresearchmag.ars.usda.gov/2006/mar/foods/"],
        "trend_type": "Original US-familiar pizza food science subject; no verified per-video virality claim",
    },
}


def verify_all() -> None:
    if set(PLANS) != {"phone", "basketball", "pizza"}:
        raise AssertionError("Require exactly three distinct US topics")
    if len({plan["topic"] for plan in PLANS.values()}) != 3:
        raise AssertionError("Topic duplicate")
    for name, plan in PLANS.items():
        pair.verify_script(plan)
        assert len(plan["source_reading"]) == 1
        print("US ORIGINAL READY", name, plan["title"], flush=True)


def main(category: str) -> None:
    if category not in PLANS:
        raise ValueError("Specify exactly phone, basketball or pizza")
    verify_all()
    gemini_transient_guard.install()
    pair.PLANS[category] = PLANS[category]
    pair.main(category)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Specify phone, basketball or pizza")
    main(sys.argv[1])

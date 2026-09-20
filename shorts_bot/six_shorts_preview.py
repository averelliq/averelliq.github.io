"""Create six distinct, licensed-HD, never-auto-published Shorts previews.

Each matrix job first downloads seven distinct real Pexels clips; it then uses a
conservative, scene-matched narration. The output is NOT approved for publication
until its 21 sampled frames and exact MP4 have been independently reviewed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pottery_preview_entry as preview
import quality_entry
import upgrade

CONFIG = {
    "3d-printer": {
        "topic": "how a filament 3d printer builds objects",
        "title": "How 3D Printing Works",
        "description": "Tiny layers turn into a real object. Watch it happen.",
        "tags": ["3D printing", "technology", "how it works"],
        "queries": ["3d printer printing plastic", "3d printer nozzle close up", "3d printing timelapse", "filament 3d printer", "3d printer working", "3d printing object", "desktop 3d printer", "3d printing close up", "3d printer machine"],
        "speech": [
            "Watch this machine build an object, one thin layer at a time.",
            "A moving nozzle follows a planned path over the print bed.",
            "It places tiny lines of softened plastic as it moves.",
            "New material settles on top of the previous printed layer.",
            "Look closely and you can see the shape slowly emerging.",
            "The machine repeats these movements to build the object higher.",
            "That's the idea: many tiny layers become one solid print.",
        ],
    },
    "bread": {
        "topic": "how bakers knead bread dough",
        "title": "Why Bakers Knead Dough",
        "description": "Fold, press, repeat. See dough change under skilled hands.",
        "tags": ["bread", "baking", "dough", "food science"],
        "queries": ["baker kneading bread dough", "hands kneading dough", "bread dough kneading closeup", "kneading dough bakery", "baker working dough", "homemade bread dough", "folding bread dough", "dough kneading hands", "bread dough preparation"],
        "speech": [
            "Why do bakers keep folding and pressing this sticky dough?",
            "Watch the hands stretch it, then push it back together.",
            "Each fold helps organize the dough into a stronger structure.",
            "The same gentle movements are repeated as the dough changes.",
            "Over time, the surface can become smoother and more elastic.",
            "A baker checks the feel before moving to the next step.",
            "Kneading develops the structure that helps bread hold its shape.",
        ],
    },
    "blacksmith": {
        "topic": "how a blacksmith forges hot metal",
        "title": "How Blacksmiths Shape Metal",
        "description": "Heat and hammer blows transform metal, one strike at a time.",
        "tags": ["blacksmith", "forging", "metalworking", "craft"],
        "queries": ["blacksmith hammering hot metal", "blacksmith forging iron", "blacksmith working anvil", "blacksmith workshop forge", "hot metal hammer blacksmith", "blacksmith sparks forging", "traditional metal forging", "blacksmith shaping steel", "forging glowing metal"],
        "speech": [
            "How can hammer blows turn solid metal into a new shape?",
            "A blacksmith heats the workpiece to make shaping it easier.",
            "Then carefully placed hammer blows begin changing its form.",
            "The metal is moved and worked from different angles.",
            "As it cools, more heat may be needed for shaping.",
            "Repeated strikes refine the shape a little at a time.",
            "It's controlled heat and careful force, not one magic hit.",
        ],
    },
    "sewing": {
        "topic": "how a sewing machine joins fabric",
        "title": "How Sewing Machines Stitch",
        "description": "Watch a needle and thread turn fabric into a seam.",
        "tags": ["sewing machine", "stitching", "fabric", "how it works"],
        "queries": ["sewing machine stitching fabric", "sewing machine needle closeup", "person sewing machine fabric", "tailor using sewing machine", "sewing fabric close up", "sewing machine working", "seam sewing machine", "sewing machine needle moving", "sewing machine hands"],
        "speech": [
            "See how quickly this machine joins two pieces of fabric.",
            "Its needle moves up and down as fabric travels underneath.",
            "The thread follows the needle through the moving cloth.",
            "A steady feed helps keep each stitch evenly spaced.",
            "Careful hands guide the fabric along the intended seam.",
            "The needle repeats its motion as the seam grows longer.",
            "That's why a machine can stitch so consistently and quickly.",
        ],
    },
    "sushi": {
        "topic": "how sushi chefs roll sushi",
        "title": "How Sushi Rolls Are Made",
        "description": "A close look at the hands behind a sushi roll.",
        "tags": ["sushi", "sushi roll", "food", "cooking"],
        "queries": ["sushi chef making sushi roll", "rolling sushi close up", "hands rolling sushi", "sushi roll preparation", "sushi making nori rice", "sushi chef rolling maki", "sushi roll bamboo mat", "making sushi rolls", "sushi roll cutting"],
        "speech": [
            "Watch how simple ingredients become a neatly shaped sushi roll.",
            "The chef arranges the ingredients before starting to roll.",
            "Careful hands bring the layers together into a compact shape.",
            "A gentle, even press helps the roll hold together.",
            "The chef checks the shape and makes small adjustments.",
            "When ready, the finished roll can be cut into pieces.",
            "The secret is patient shaping, not just rolling it fast.",
        ],
    },
    "flowers": {
        "topic": "how florists arrange a flower bouquet",
        "title": "How Bouquets Take Shape",
        "description": "See flowers become a bouquet, stem by stem.",
        "tags": ["flowers", "bouquet", "florist", "craftsmanship"],
        "queries": ["florist arranging bouquet", "hands making flower bouquet", "flower arrangement florist", "florist workshop flowers", "bouquet making close up", "florist wrapping bouquet", "fresh flowers arranging", "bouquet floral design", "florist hands roses"],
        "speech": [
            "How do separate flowers turn into one balanced bouquet?",
            "A florist brings stems together and checks their positions.",
            "Different flowers add changes in height, shape, and texture.",
            "Small adjustments help the arrangement look balanced from different sides.",
            "The florist keeps rearranging stems until the shape feels right.",
            "Wrapping or tying the stems helps hold everything together.",
            "That's the craft: arranging individual flowers into one composition.",
        ],
    },
}


def main() -> None:
    name = os.environ.get("SHORTS_BATCH_TOPIC", "")
    if name not in CONFIG:
        raise ValueError("Unknown six-short request; refuse accidental publication")
    if os.environ.get("SHORTS_SKIP_UPLOAD") != "1":
        raise ValueError("Batch preview MUST NOT publish before audiovisual review")
    config = CONFIG[name]
    request = json.loads((Path(__file__).parent / "six_shorts_request.json").read_text())
    if request.get("preview_only") is not True or request.get("topics") != list(CONFIG):
        raise ValueError("Batch request does not match approved six subjects")
    assert len(config["speech"]) == 7 and len(config["queries"]) >= 7
    preview.TOPIC = config["topic"]
    preview.SEARCHES = tuple(config["queries"])
    preview.SPEECH = tuple(config["speech"])
    preview.CAPTIONS = ("Look closer", "The first move", "Building the shape", "Watch the change", "Careful adjustments", "Almost finished", "Now you know")
    preview.MAX_CANDIDATES = 85
    preview.MAX_DOWNLOADS = 34
    upgrade.aligned_build_video = quality_entry._original_build
    print(f"SIX SHORTS PREVIEW: {name}; 7 unique filmed native-HD clips required; upload OFF", flush=True)
    preview.main()
    output = upgrade.bot.OUT
    plan_file = output / "plan.json"
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if plan.get("topic") != config["topic"] or len(plan.get("scenes", [])) != 7:
        raise ValueError("Preview subject mismatch; no release")
    plan.update(title=config["title"], description=config["description"], tags=config["tags"], batch_topic=name)
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"SIX SHORTS PREVIEW READY: {name}; title={config['title']}; review before upload", flush=True)


if __name__ == "__main__":
    main()

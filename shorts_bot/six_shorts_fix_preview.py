"""Re-render four rejected previews; never publish until new MP4 review."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pottery_preview_entry as footage
import six_shorts_preview as batch

REJECTED = {
    "3d-printer": {7480058, 7088468},  # Drill press and unrelated device wiring.
    "bread": {6139593},              # Dark modeling material, not bread dough.
    "sewing": {20757503},            # Rotary cutting machine, not sewing.
    "sushi": set(),
}
UPDATES = {
    "3d-printer": {
        3: "As the nozzle moves, more layers build up on the object.",
        4: "Look closely: each new pass adds material on top.",
        5: "You can watch the printed shape slowly emerge.",
        6: "Layer after layer, the printer keeps building the object.",
        7: "Once complete, the finished part can be lifted away.",
    },
    "sewing": {
        5: "Careful hands adjust the machine before the next seam.",
    },
    "sushi": {
        5: "The chef prepares fresh filling with careful, precise cuts.",
        6: "Then ingredients are placed so the roll holds together.",
        7: "One final cut reveals the finished sushi pieces.",
    },
}


def main():
    name = os.environ.get("SHORTS_BATCH_TOPIC", "")
    if name not in REJECTED or os.environ.get("SHORTS_SKIP_UPLOAD") != "1":
        raise ValueError("Invalid correction-only preview request")
    request = json.loads((Path(__file__).parent / "six_shorts_fix_request.json").read_text())
    if not request.get("preview_only") or request.get("topics") != list(REJECTED):
        raise ValueError("Unexpected correction request")
    cfg = batch.CONFIG[name]
    speech = cfg["speech"][:]
    for scene, text in UPDATES.get(name, {}).items():
        speech[scene - 1] = text
    cfg["speech"] = speech
    original_recover = footage.recover

    def only_approved_candidates(pool, work):
        filtered = [candidate for candidate in pool if candidate["id"] not in REJECTED[name]]
        print(f"CORRECTION: excluded visually unrelated IDs for {name}: {sorted(REJECTED[name])}", flush=True)
        found = original_recover(filtered, work)
        if name == "3d-printer":
            # A valid filmed removal of the completed print is the closing shot,
            # not a shot of live deposition during narration about printing.
            removal = [x for x in found if x["id"] == 26621091]
            if len(removal) != 1:
                raise ValueError("Required observed final printed-part removal clip absent")
            found = [x for x in found if x["id"] != 26621091] + removal
        return found

    footage.recover = only_approved_candidates
    try:
        batch.main()
    finally:
        footage.recover = original_recover


if __name__ == "__main__":
    main()

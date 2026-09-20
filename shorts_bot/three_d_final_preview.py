"""Third 3D-printer preview: reject office printers and insist on filament footage."""
from __future__ import annotations

import json
import os
from pathlib import Path

import six_shorts_fix_preview as correction
import six_shorts_preview as batch


def main():
    if os.environ.get("SHORTS_BATCH_TOPIC") != "3d-printer" or os.environ.get("SHORTS_SKIP_UPLOAD") != "1":
        raise ValueError("Only approved 3D printer preview permitted")
    request = json.loads((Path(__file__).parent / "three_d_final_request.json").read_text())
    if request.get("preview_only") is not True or request.get("topic") != "3d-printer":
        raise ValueError("Invalid focused preview request")
    batch.CONFIG["3d-printer"]["queries"] = [
        "3d printer printing plastic", "filament 3d printer", "3d printing timelapse",
        "desktop 3d printer", "3d printer making object", "3d printing close up",
        "FDM printer printing object", "3d printer working", "3d printer extruder",
    ]
    correction.REJECTED["3d-printer"].update({36570936, 36570946})
    correction.main()


if __name__ == "__main__":
    main()

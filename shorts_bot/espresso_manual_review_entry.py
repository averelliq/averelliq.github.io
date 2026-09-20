"""Preview-only espresso edit; keep codec and stock checks; never publish.

The separate Gemini final-scene review is not available under current quota.
For this PREVIEW only, retain every pre-approved real-footage/source/codec
check and explicitly require human inspection of MP4 before release.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import espresso_direct_preview as preview
import quality_entry
import upgrade


def main() -> None:
    if os.environ.get("SHORTS_SKIP_UPLOAD") != "1":
        raise RuntimeError("Preview-only script MUST NOT have YouTube upload enabled")
    shots = list(preview.SHOTS)
    opening = list(shots[0])
    opening[3] = ("Why does an espresso machine make such a concentrated shot? "
                  "First, the portafilter goes into place.")
    opening[4] = "How espresso starts"
    shots[0] = tuple(opening)
    steam = list(shots[3])
    steam[3] = "Watch the flow continue as fresh espresso collects in the cup."
    steam[4] = "The extraction continues"
    shots[3] = tuple(steam)
    preview.SHOTS = tuple(shots)
    # quality_entry wraps upgrade's actual renderer with an additional Gemini
    # final visual check. That external service is quota-blocked. For PREVIEW
    # ONLY run the ORIGINAL renderer, which still invokes upgrade.check_video,
    # then export frames for direct visual inspection before any publication.
    upgrade.aligned_build_video = quality_entry._original_build
    print("PREVIEW NOTE: Independent final Gemini visual check unavailable; "
          "manual audiovisual review of exported MP4 required BEFORE publishing.", flush=True)
    preview.main()
    out = upgrade.bot.OUT
    video = out / "short.mp4"
    info = upgrade.check_video(video)
    frames = sorted(out.glob("scene_*.jpg"))
    if len(frames) < 6:
        raise ValueError(f"Expected all scene-review frames, got {len(frames)}")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"],
                   check=True, capture_output=True)
    plan_path = out / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if "portafilter goes into place" not in plan["scenes"][0]["voiceover"]:
        raise ValueError("First scene still contains inaccurate grinding claim")
    (out / "manual_review_required.txt").write_text(
        "Format/decoder tests PASSED; independent final Gemini visual review NOT RUN. "
        "Review the actual MP4 picture, subtitles and narration before public release.\n",
        encoding="utf-8",
    )
    print(f"PREVIEW READY FOR MANUAL REVIEW: {video} / {info} / "
          f"{len(frames)} scene stills / YouTube upload DISABLED", flush=True)


if __name__ == "__main__":
    main()

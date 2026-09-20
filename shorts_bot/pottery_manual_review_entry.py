"""Preview only: truthful clay-shaping narration, with manual audiovisual review.

The external Gemini final-scene review is unavailable in this preview job;
publishing remains forbidden. The native renderer retains full-HD/codec gates.
"""
from __future__ import annotations

import os

import pottery_preview_entry as pottery
import quality_entry
import upgrade

TOPIC = "how a potter shapes clay on a spinning wheel"
SPEECH = (
    "How do potters turn spinning clay into different shapes?",
    "Their hands steady the wet clay while the wheel keeps turning.",
    "With water and gentle pressure, they open up the center.",
    "A small tool can refine the rim as the piece spins.",
    "Careful fingers smooth the walls and define their shape.",
    "Even tiny touches make a difference along the soft edge.",
    "After shaping, the clay must dry and be fired before use.",
)
CAPTIONS = (
    "Spinning clay", "Steady hands", "Opening the center", "Refining the rim",
    "Shaping the walls", "Tiny adjustments", "Dry, then fire",
)


def main() -> None:
    if os.environ.get("SHORTS_SKIP_UPLOAD") != "1":
        raise RuntimeError("Never bypass the final visual review in a publishing workflow")
    pottery.TOPIC = TOPIC
    pottery.SPEECH = SPEECH
    pottery.CAPTIONS = CAPTIONS
    original_build = quality_entry._original_build

    def truthful_preview_build(plan, voice):
        if plan.get("topic") != TOPIC or len(plan.get("scenes", [])) != 7:
            raise ValueError("Unexpected pottery subject or scene count")
        plan["title"] = "How Potters Shape Spinning Clay"
        plan["description"] = (
            "Watch skilled hands shape wet clay on a spinning pottery wheel, "
            "from opening the center to refining the rim."
        )
        return original_build(plan, voice)

    upgrade.aligned_build_video = truthful_preview_build
    print("PREVIEW ONLY: corrected clay-shaping story; manual MP4 review is mandatory before release", flush=True)
    pottery.main()


if __name__ == "__main__":
    main()

"""Correct the first hook before launching the single authorized octopus Short.

The original GitHub job stopped at preflight and skipped YouTube upload. Launch
through a new commit, never GitHub's re-run action, to prevent uncertain repeats.
"""
from __future__ import annotations

import one_octopus_live_20260918 as short


def apply_fix() -> None:
    short.PLAN["scenes"][0]["voiceover"] = (
        "Three hearts. Blue blood. Eight astonishing arms. "
        "Meet the octopus, the ocean's remarkable escape artist."
    )


if __name__ == "__main__":
    apply_fix()
    short.main()

"""Prevent truncated Gemini footage JSON from crashing a whole production.

Split image-heavy reviews into small independent, fully validated batches.
Every clip must pass the ORIGINAL conservative review; invalid responses NEVER
become approval and all existing independent visual/final gates remain in place.
"""
from __future__ import annotations

import json

import footage_first

_installed = False


def install() -> None:
    global _installed
    if _installed:
        return
    original_vision = footage_first._vision

    def review_in_small_batches(topic, items):
        decisions = []
        for start in range(0, len(items), 2):
            batch = items[start:start + 2]
            try:
                decisions.extend(original_vision(topic, batch))
                continue
            except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
                print(
                    f"FOOTAGE REVIEW: invalid/incomplete batch {start + 1}-"
                    f"{start + len(batch)} ({type(exc).__name__}); retry each clip separately",
                    flush=True,
                )
            for item in batch:
                accepted = False
                for attempt in range(2):
                    try:
                        verdict = original_vision(topic, [item])
                        accepted = len(verdict) == 1 and verdict[0] is True
                        break
                    except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
                        print(
                            f"FOOTAGE REVIEW: clip {item['id']} response invalid "
                            f"({type(exc).__name__}, attempt {attempt + 1}/2); "
                            "never assume approval",
                            flush=True,
                        )
                decisions.append(accepted)
        if len(decisions) != len(items):
            raise ValueError("Footage review count inconsistent; upload cancelled")
        return decisions

    footage_first._vision = review_in_small_batches
    _installed = True

"""Re-render the grape-only Short with narration matching the observed final shot.

The final video depicts fingers squeezing whole grapes but does not visibly
show juice leaving the skins. Never claim unseen juice is visible in that shot.
Preview only; publication requires review of its exact MP4 and sampled frames.
"""
from __future__ import annotations

import grape_accurate_preview as grape

grape.SPEECH = grape.SPEECH[:-1] + (
    "A gentle squeeze puts pressure on each grape, just like the larger pressing process.",
)
grape.CAPTIONS = grape.CAPTIONS[:-1] + ("Squeezing grapes",)

if __name__ == "__main__":
    grape.main()

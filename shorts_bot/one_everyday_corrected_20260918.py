"""One-shot soda upload with a shorter opening hook; never rerun after upload."""
from __future__ import annotations

import two_original_shorts_20260918 as pair


def main() -> None:
    plan = pair.PLANS["everyday"]
    plan["scenes"][0]["voiceover"] = (
        "Soda bubbles are escaping gas. Why do they race upward?"
    )
    pair.main("everyday")


if __name__ == "__main__":
    main()

"""One-shot soda video after a CONFIRMED pre-upload HTTP 503 final-review outage.

No model outage or rejected shot ever authorizes an upload. Do not rerun this
workflow after an ambiguous upload response.
"""
from __future__ import annotations

import gemini_transient_guard
import one_everyday_soda_finalshot_20260918 as soda


def main() -> None:
    gemini_transient_guard.install()
    soda.main()


if __name__ == "__main__":
    main()

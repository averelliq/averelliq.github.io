"""Bind pottery release to the complete seven-scene manually checked preview."""
from __future__ import annotations

import publish_reviewed_pottery as publish

publish.PREVIEW_RUN = 35480929909

if __name__ == "__main__":
    publish.main()

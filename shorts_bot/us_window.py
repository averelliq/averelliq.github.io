"""US publication windows. UTC GitHub cron candidates are filtered by real New York time.

Three daily slots are 16:15, 19:15 and 22:15 America/New_York.
These correspond to 13:15, 16:15, 19:15 America/Los_Angeles.
The gate does not claim universal or channel-specific peak viewing times.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
PACIFIC = ZoneInfo("America/Los_Angeles")
SLOTS = {16: "science", 19: "history", 22: "everyday"}


def publication_slot(now: datetime) -> tuple[bool, str, str]:
    """Return (due, theme, local-time description) for an aware datetime."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Publication gate needs a timezone-aware datetime")
    east = now.astimezone(EASTERN)
    west = now.astimezone(PACIFIC)
    due = east.minute == 15 and east.hour in SLOTS
    theme = SLOTS[east.hour] if due else ""
    label = f"US Eastern {east:%Y-%m-%d %H:%M %Z}; Pacific {west:%Y-%m-%d %H:%M %Z}"
    return due, theme, label


if __name__ == "__main__":
    run, theme, label = publication_slot(datetime.now(timezone.utc))
    print(f"US publication window: due={run}; theme={theme or 'none'}; {label}", flush=True)

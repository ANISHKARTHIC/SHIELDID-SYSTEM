from datetime import datetime, timezone
from typing import Optional


def to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """
    Serializes a datetime as an unambiguous UTC ISO-8601 string (with a
    'Z'/offset suffix), for any client-facing JSON field carrying a
    time-of-day.

    Every timestamp column in this app is written as
    `datetime.now(timezone.utc)`, but SQLite/Postgres TIMESTAMP WITHOUT
    TIME ZONE columns silently drop the tzinfo on write and read it back
    naive — so `dt.isoformat()` on a value read from the DB produces a
    string with no timezone marker at all (e.g. "2026-09-08T17:57:16"),
    even though the underlying instant is UTC. JS `new Date(...)` (and
    other ISO-8601 parsers) treat an offset-less string as *local* time,
    silently shifting every timestamp shown to the operator by the
    browser's UTC offset. Since every value here is known-UTC even when
    naive, attaching tzinfo=utc before formatting is correct, not a guess.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

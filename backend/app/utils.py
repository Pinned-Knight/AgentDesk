from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC timestamp — the form MongoDB hands back, so reads and writes compare cleanly."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") + "Z" if dt else None

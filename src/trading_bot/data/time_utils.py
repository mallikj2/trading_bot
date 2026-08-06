"""Timezone and interval helpers used throughout the data kernel."""

from __future__ import annotations

from datetime import datetime, timezone

from .errors import DataContractError

UTC = timezone.utc


def require_aware(value: datetime, field_name: str = "datetime") -> datetime:
    """Return *value* normalized to UTC, rejecting naive datetimes."""
    if not isinstance(value, datetime):
        raise DataContractError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise DataContractError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def interval_contains(
    instant: datetime,
    start: datetime,
    end: datetime | None,
) -> bool:
    """Evaluate a half-open effective interval ``[start, end)`` in UTC."""
    instant_utc = require_aware(instant, "instant")
    start_utc = require_aware(start, "start")
    if end is None:
        return instant_utc >= start_utc
    end_utc = require_aware(end, "end")
    if end_utc <= start_utc:
        raise DataContractError("interval end must be later than start")
    return start_utc <= instant_utc < end_utc

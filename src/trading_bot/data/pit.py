"""Generic point-in-time selection and availability propagation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Iterable, Protocol, TypeVar

from .errors import PointInTimeError
from .time_utils import require_aware


class PITRecord(Protocol):
    available_at: datetime
    revision: int


T = TypeVar("T", bound=PITRecord)


def select_latest_known(
    records: Iterable[T],
    *,
    decision_at: datetime,
    predicate: Callable[[T], bool] | None = None,
) -> T:
    """Select the latest revision known by ``decision_at``.

    No future fallback is permitted. Conflicting records with the same latest
    availability and revision fail closed.
    """
    decision = require_aware(decision_at, "decision_at")
    eligible: list[T] = []
    for record in records:
        if predicate is not None and not predicate(record):
            continue
        available = require_aware(record.available_at, "record.available_at")
        if available <= decision:
            eligible.append(record)
    if not eligible:
        raise PointInTimeError("no point-in-time record was available")
    latest_key = max(
        (require_aware(record.available_at, "record.available_at"), int(record.revision))
        for record in eligible
    )
    latest = [
        record
        for record in eligible
        if (require_aware(record.available_at, "record.available_at"), int(record.revision))
        == latest_key
    ]
    if len({repr(record) for record in latest}) > 1:
        raise PointInTimeError(
            "conflicting point-in-time records share the latest availability and revision"
        )
    return latest[0]


def derive_feature_available_at(
    input_available_at: Iterable[datetime],
    *,
    processing_latency: timedelta = timedelta(0),
) -> datetime:
    values = [require_aware(value, "input available_at") for value in input_available_at]
    if not values:
        raise PointInTimeError("feature requires at least one input timestamp")
    if processing_latency < timedelta(0):
        raise PointInTimeError("processing_latency cannot be negative")
    return max(values) + processing_latency

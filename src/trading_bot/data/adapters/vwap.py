"""Validated Phase 01 next-session 10:00-10:30 ET VWAP construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Iterable
from uuid import UUID
from zoneinfo import ZoneInfo

from ..contracts import DataQualityStatus
from ..errors import DataContractError, PointInTimeError
from ..time_utils import require_aware
from .models import IntradayBar

NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class ExecutionVwap:
    instrument_id: UUID
    symbol: str
    session_date: date
    window_start: datetime
    window_end: datetime
    interval_count: int
    total_volume: int
    vwap: Decimal
    available_at: datetime
    source_snapshot_ids: tuple[str, ...]


def build_execution_vwap(
    bars: Iterable[IntradayBar],
    *,
    session_date: date,
    decision_at: datetime,
    expected_interval_minutes: int = 5,
) -> ExecutionVwap:
    if expected_interval_minutes <= 0 or 30 % expected_interval_minutes != 0:
        raise ValueError("expected_interval_minutes must divide 30")
    decision = require_aware(decision_at, "decision_at")
    rows = tuple(bars)
    if not rows:
        raise DataContractError("VWAP input bars are empty")
    identities = {(row.instrument_id, row.symbol) for row in rows}
    if len(identities) != 1:
        raise DataContractError("VWAP bars must reference one instrument and symbol")

    expected_local_starts = {
        time(10, minute)
        for minute in range(0, 30, expected_interval_minutes)
    }
    selected: dict[time, IntradayBar] = {}
    for row in rows:
        if row.session_date != session_date:
            continue
        local_start = row.interval_start.astimezone(NEW_YORK)
        local_end = row.interval_end.astimezone(NEW_YORK)
        start_time = local_start.time().replace(tzinfo=None)
        if start_time not in expected_local_starts:
            continue
        if local_end - local_start != timedelta(minutes=expected_interval_minutes):
            raise DataContractError("VWAP interval length does not match configured frequency")
        if start_time in selected:
            raise DataContractError(f"duplicate VWAP interval at {start_time}")
        selected[start_time] = row

    missing = expected_local_starts.difference(selected)
    if missing:
        raise DataContractError(f"incomplete VWAP window; missing={sorted(missing)}")

    total_volume = 0
    weighted = Decimal("0")
    available_at = None
    for start_time in sorted(selected):
        row = selected[start_time]
        if row.quality_status != DataQualityStatus.VALID:
            raise DataContractError(f"invalid VWAP interval quality at {start_time}")
        if row.volume <= 0:
            raise DataContractError(f"zero-volume VWAP interval at {start_time}")
        if row.available_at > decision:
            raise PointInTimeError("VWAP interval was not available at simulated fill time")
        weighted += row.vwap * Decimal(row.volume)
        total_volume += row.volume
        available_at = row.available_at if available_at is None else max(available_at, row.available_at)

    first = selected[min(selected)]
    last = selected[max(selected)]
    assert available_at is not None
    return ExecutionVwap(
        instrument_id=first.instrument_id,
        symbol=first.symbol,
        session_date=session_date,
        window_start=first.interval_start,
        window_end=last.interval_end,
        interval_count=len(selected),
        total_volume=total_volume,
        vwap=weighted / Decimal(total_volume),
        available_at=available_at,
        source_snapshot_ids=tuple(sorted({row.source_snapshot_id for row in selected.values()})),
    )

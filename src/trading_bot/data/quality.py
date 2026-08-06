"""Deterministic data-quality checks."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from .contracts import DailyBar
from .errors import DataContractError


def validate_daily_bars(bars: Iterable[DailyBar]) -> tuple[DailyBar, ...]:
    rows = tuple(bars)
    if not rows:
        raise DataContractError("daily bar dataset is empty")
    by_key: dict[tuple[object, object], list[DailyBar]] = defaultdict(list)
    for bar in rows:
        by_key[(bar.instrument_id, bar.session_date)].append(bar)
    for key, revisions in by_key.items():
        seen = {(bar.provider_revision, bar.snapshot_id) for bar in revisions}
        if len(seen) != len(revisions):
            raise DataContractError(f"duplicate daily bar revision: {key}")
    return tuple(sorted(rows, key=lambda bar: (bar.instrument_id.hex, bar.session_date, bar.provider_revision)))


def raw_dollar_volume(bar: DailyBar) -> Decimal:
    return bar.close * Decimal(bar.volume)

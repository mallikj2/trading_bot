"""Bridge point-in-time total-return builds to the Phase 01 strategy schema."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from .contracts import DailyBar
from .errors import DataContractError
from .total_returns import TotalReturnBuild


@dataclass(frozen=True, slots=True)
class StrategyPriceRecord:
    session_date: date
    instrument_id: UUID
    raw_close: Decimal
    raw_volume: int
    adjusted_close: Decimal
    price_eligibility_close: Decimal
    adjustment_version: str


def strategy_price_records(
    build: TotalReturnBuild,
    *,
    bars: Iterable[DailyBar],
) -> tuple[StrategyPriceRecord, ...]:
    """Return strategy-ready price fields without future-action leakage.

    ``adjusted_close`` is the forward total-return index. Its arbitrary level
    does not affect returns, momentum, trend comparisons, volatility, or
    correlations. ``price_eligibility_close`` is the current-session raw close,
    equivalent to an as-of-current-session split-adjusted close and therefore
    not rewritten by a later split.
    """
    bars_by_date = {
        bar.session_date: bar
        for bar in bars
        if bar.instrument_id == build.instrument_id and bar.available_at <= build.decision_at
    }
    output: list[StrategyPriceRecord] = []
    for observation in build.total_returns:
        if observation.terminal:
            continue
        if observation.session_date not in bars_by_date or observation.raw_close is None:
            raise DataContractError(
                f"missing daily bar for total-return observation {observation.session_date}"
            )
        bar = bars_by_date[observation.session_date]
        if bar.close != observation.raw_close:
            raise DataContractError(
                f"raw close mismatch for {observation.session_date}: {bar.close} != {observation.raw_close}"
            )
        output.append(
            StrategyPriceRecord(
                session_date=bar.session_date,
                instrument_id=build.instrument_id,
                raw_close=bar.close,
                raw_volume=bar.volume,
                adjusted_close=observation.total_return_index,
                price_eligibility_close=bar.close,
                adjustment_version=build.build_hash,
            )
        )
    return tuple(output)

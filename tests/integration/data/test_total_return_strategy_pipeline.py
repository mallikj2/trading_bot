from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal
from uuid import UUID

import numpy as np
import pandas as pd
import pytest

from trading_bot.data.contracts import CorporateAction, CorporateActionType, DailyBar
from trading_bot.data.strategy_inputs import strategy_price_records
from trading_bot.data.total_returns import (
    DEFAULT_REQUIRED_COVERAGE_TYPES,
    CorporateActionCoverage,
    build_total_return_as_of,
)
from trading_bot.strategies.csmom_ls_v0_2 import compute_features

UTC = timezone.utc
INSTRUMENT = UUID("10000000-0000-0000-0000-000000000001")


def at_utc(session_date, hour, minute=0):
    return datetime.combine(session_date, time(hour, minute), tzinfo=UTC)


def test_point_in_time_total_return_pipeline_feeds_phase01_without_action_jumps():
    sessions = pd.bdate_range("2024-01-02", periods=305)
    split_index = 150
    dividend_index = 220
    closes: list[Decimal] = [Decimal("100")]
    volumes: list[int] = [1_000_000]
    for index in range(1, len(sessions)):
        prior = closes[-1]
        next_close = prior * Decimal("1.001")
        next_volume = volumes[-1]
        if index == split_index:
            next_close = next_close / Decimal("2")
            next_volume = next_volume * 2
        if index == dividend_index:
            next_close = next_close - Decimal("1")
        closes.append(next_close)
        volumes.append(next_volume)

    bars = []
    for stamp, close, volume in zip(sessions, closes, volumes, strict=True):
        session_date = stamp.date()
        bars.append(
            DailyBar(
                instrument_id=INSTRUMENT,
                session_date=session_date,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=volume,
                observed_at=at_utc(session_date, 20),
                available_at=at_utc(session_date, 20, 30),
                snapshot_id=f"bar-{session_date}",
            )
        )

    split_date = sessions[split_index].date()
    dividend_date = sessions[dividend_index].date()
    actions = [
        CorporateAction(
            action_id="integration-split",
            instrument_id=INSTRUMENT,
            action_type=CorporateActionType.SPLIT,
            effective_at=at_utc(split_date, 13, 30),
            available_at=at_utc(split_date, 13, 30),
            source_snapshot_id="split-source",
            split_old_shares=Decimal("1"),
            split_new_shares=Decimal("2"),
        ),
        CorporateAction(
            action_id="integration-dividend",
            instrument_id=INSTRUMENT,
            action_type=CorporateActionType.CASH_DIVIDEND,
            effective_at=at_utc(dividend_date, 13, 30),
            available_at=at_utc(dividend_date, 13, 30),
            source_snapshot_id="dividend-source",
            cash_amount=Decimal("1"),
            currency="USD",
        ),
    ]
    decision_at = at_utc(sessions[-1].date(), 21)
    coverage = CorporateActionCoverage(
        instrument_id=INSTRUMENT,
        covered_through=at_utc(sessions[-1].date(), 23, 59),
        available_at=at_utc(sessions[-1].date(), 20, 31),
        covered_types=DEFAULT_REQUIRED_COVERAGE_TYPES,
        source_snapshot_id="coverage-source",
        complete=True,
    )
    build = build_total_return_as_of(
        instrument_id=INSTRUMENT,
        bars=bars,
        actions=actions,
        valuations=[],
        coverage=[coverage],
        decision_at=decision_at,
    )
    price_records = strategy_price_records(build, bars=bars)
    frame = pd.DataFrame(
        [
            {
                "session_date": item.session_date,
                "instrument_id": str(item.instrument_id),
                "symbol": "TEST",
                "raw_close": float(item.raw_close),
                "adjusted_close": float(item.adjusted_close),
                "price_eligibility_close": float(item.price_eligibility_close),
                "raw_volume": item.raw_volume,
                "market_cap": 5_000_000_000.0,
                "exchange": "NYSE",
                "security_type": "COMMON_STOCK",
                "sector": "FF12_12_OTHER",
                "data_quality_status": "VALID",
            }
            for item in price_records
        ]
    )
    features = compute_features(frame)
    split_row = features.loc[features["session_date"].eq(pd.Timestamp(split_date))].iloc[0]
    dividend_row = features.loc[features["session_date"].eq(pd.Timestamp(dividend_date))].iloc[0]
    expected = np.log(1.001)
    assert split_row["log_return"] == pytest.approx(expected, abs=1e-12)
    assert dividend_row["log_return"] == pytest.approx(expected, abs=1e-12)
    assert split_row["price_eligibility_close"] == pytest.approx(float(closes[split_index]))
    before_split_dv = features.iloc[split_index - 1]["raw_dollar_volume"]
    split_dv = split_row["raw_dollar_volume"]
    assert split_dv == pytest.approx(before_split_dv * 1.001, rel=1e-12)

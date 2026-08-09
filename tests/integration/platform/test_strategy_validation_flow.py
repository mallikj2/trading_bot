from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from trading_bot.platform.strategy_validation import (
    CsmomSnapshotEvaluator,
    DecisionSnapshot,
    ValidationStatus,
    validate_lookahead,
    validate_recursive_stability,
)

UTC = timezone.utc


def _panel(sessions: int = 365, symbols: int = 20) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=sessions)
    rows = []
    for idx, slope in enumerate(np.linspace(-0.0015, 0.0015, symbols)):
        t = np.arange(sessions)
        close = 100 * np.exp(t * slope + 0.002 * np.sin(t / 13 + idx))
        for d, px in zip(dates, close, strict=True):
            rows.append({
                "session_date": d,
                "instrument_id": f"ID{idx:03d}",
                "symbol": f"S{idx:02d}",
                "raw_close": float(px),
                "adjusted_close": float(px),
                "price_eligibility_close": float(px),
                "raw_volume": 1_000_000,
                "market_cap": 5_000_000_000,
                "exchange": "NYSE" if idx % 2 == 0 else "NASDAQ",
                "security_type": "COMMON_STOCK",
                "sector": f"SEC{idx % 6}",
                "data_quality_status": "VALID",
                "entry_blocked": False,
            })
    return pd.DataFrame(rows)


def test_clean_full_to_truncated_and_warmup_flow_passes() -> None:
    frame = _panel()
    decision = pd.to_datetime(frame["session_date"]).max().normalize()
    at = datetime(2026, 8, 8, 22, 0, tzinfo=UTC)
    lookahead = validate_lookahead(frame, decision_dates=[decision], generated_at=at)
    recursive = validate_recursive_stability(
        frame,
        decision_dates=[decision],
        warmup_sessions=(300, 320, 360),
        generated_at=at,
    )
    assert lookahead.status is ValidationStatus.PASS
    assert recursive.status is ValidationStatus.PASS


def test_adversarial_future_rank_change_fails_closed() -> None:
    frame = _panel()
    decision = sorted(pd.to_datetime(frame["session_date"]).dt.normalize().unique())[-5]
    clean = CsmomSnapshotEvaluator()

    def leaky(data: pd.DataFrame, when: pd.Timestamp) -> DecisionSnapshot:
        snapshot = clean(data, when)
        future_rows = pd.to_datetime(data["session_date"]).dt.normalize().gt(when).sum()
        return replace(snapshot, ranking=tuple(snapshot.ranking) + ({"future_rows": int(future_rows)},))

    report = validate_lookahead(frame, decision_dates=[decision], evaluator=leaky)
    assert report.status is ValidationStatus.FAIL
    assert report.differences[0].challenger_label == "TRUNCATED_AT_DECISION"

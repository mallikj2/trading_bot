from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from trading_bot.platform.strategy_validation import (
    CsmomSnapshotEvaluator,
    DecisionSnapshot,
    ValidationContractError,
    ValidationKind,
    ValidationStatus,
    csmom_decision_snapshot,
    validate_lookahead,
    validate_recursive_stability,
    validate_strategy_bias_suite,
)

UTC = timezone.utc


def make_panel(symbols: int = 20, sessions: int = 365) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=sessions)
    rows: list[dict[str, object]] = []
    slopes = np.linspace(-0.0015, 0.0015, symbols)
    for idx, slope in enumerate(slopes):
        t = np.arange(sessions)
        adjusted = 100.0 * np.exp(t * slope + 0.002 * np.sin(t / 11.0 + float(idx)))
        for session_date, close in zip(dates, adjusted, strict=True):
            rows.append(
                {
                    "session_date": session_date,
                    "instrument_id": f"ID{idx:03d}",
                    "symbol": f"S{idx:02d}",
                    "raw_close": float(close),
                    "adjusted_close": float(close),
                    "price_eligibility_close": float(close),
                    "raw_volume": 1_000_000.0,
                    "market_cap": 5_000_000_000.0,
                    "exchange": "NYSE" if idx % 2 == 0 else "NASDAQ",
                    "security_type": "COMMON_STOCK",
                    "sector": f"SECTOR{idx % 6}",
                    "data_quality_status": "VALID",
                    "entry_blocked": False,
                }
            )
    return pd.DataFrame(rows)


def final_decisions(frame: pd.DataFrame, count: int = 3) -> list[pd.Timestamp]:
    dates = sorted(pd.to_datetime(frame["session_date"]).dt.normalize().unique())
    return [pd.Timestamp(value) for value in dates[-count:]]


def test_clean_strategy_passes_lookahead() -> None:
    frame = make_panel()
    report = validate_lookahead(
        frame,
        decision_dates=final_decisions(frame, 1),
        generated_at=datetime(2026, 8, 8, 22, 0, tzinfo=UTC),
    )
    assert report.status is ValidationStatus.PASS
    assert report.differences == ()
    assert report.comparisons == 1


def test_clean_strategy_passes_recursive_stability() -> None:
    frame = make_panel()
    report = validate_recursive_stability(
        frame,
        decision_dates=final_decisions(frame, 1),
        warmup_sessions=(300, 320, 360),
        generated_at=datetime(2026, 8, 8, 22, 0, tzinfo=UTC),
    )
    assert report.status is ValidationStatus.PASS
    assert report.differences == ()
    assert report.comparisons == 3


def test_snapshot_contains_all_required_decision_sections() -> None:
    frame = make_panel()
    decision = final_decisions(frame, 1)[0]
    snapshot = csmom_decision_snapshot(frame, decision)
    assert snapshot.features
    assert snapshot.universe
    assert snapshot.ranking
    assert snapshot.candidates
    assert snapshot.targets
    assert set(snapshot.section_hashes) == {"FEATURES", "UNIVERSE", "RANKING", "CANDIDATES", "TARGETS", "EXITS"}


def test_future_rows_do_not_change_clean_snapshot_hash() -> None:
    frame = make_panel()
    decision = final_decisions(frame, 3)[0]
    evaluator = CsmomSnapshotEvaluator()
    full = evaluator(frame, decision)
    truncated = evaluator(frame.loc[pd.to_datetime(frame["session_date"]).dt.normalize().le(decision)], decision)
    assert full.state_hash == truncated.state_hash


class FutureLeakingEvaluator:
    """Adversarial fixture that illegally reads the last row in the supplied frame."""

    def __init__(self) -> None:
        self.clean = CsmomSnapshotEvaluator()

    def __call__(self, frame: pd.DataFrame, decision_date: pd.Timestamp) -> DecisionSnapshot:
        clean = self.clean(frame, decision_date)
        future_marker = float(frame.sort_values("session_date").iloc[-1]["adjusted_close"])
        contaminated = tuple(clean.ranking) + ({"future_marker": f"{future_marker:.12f}"},)
        return replace(clean, ranking=contaminated)


def test_contaminated_evaluator_fails_lookahead() -> None:
    frame = make_panel()
    report = validate_lookahead(
        frame,
        decision_dates=[final_decisions(frame, 4)[0]],
        evaluator=FutureLeakingEvaluator(),
    )
    assert report.status is ValidationStatus.FAIL
    assert any(diff.section.value == "RANKING" for diff in report.differences)
    assert all(diff.kind is ValidationKind.LOOKAHEAD for diff in report.differences)


class RecursiveLeakingEvaluator:
    """Adversarial fixture whose output depends on the arbitrary history start."""

    def __init__(self) -> None:
        self.clean = CsmomSnapshotEvaluator()

    def __call__(self, frame: pd.DataFrame, decision_date: pd.Timestamp) -> DecisionSnapshot:
        clean = self.clean(frame, decision_date)
        sessions = len(pd.to_datetime(frame["session_date"]).dt.normalize().unique())
        contaminated = tuple(clean.features) + ({"history_length": sessions},)
        return replace(clean, features=contaminated)


def test_contaminated_evaluator_fails_recursive_stability() -> None:
    frame = make_panel()
    report = validate_recursive_stability(
        frame,
        decision_dates=[final_decisions(frame, 1)[0]],
        warmup_sessions=(300, 320, 360),
        evaluator=RecursiveLeakingEvaluator(),
    )
    assert report.status is ValidationStatus.FAIL
    assert len(report.differences) == 3
    assert all(diff.section.value == "FEATURES" for diff in report.differences)
    assert all(diff.kind is ValidationKind.RECURSIVE for diff in report.differences)


def test_exit_decisions_are_covered_by_lookahead_comparison() -> None:
    frame = make_panel()

    def leaky_exit(data: pd.DataFrame, decision: pd.Timestamp):
        last_date = pd.to_datetime(data["session_date"]).max().normalize()
        return [
            {
                "instrument_id": "ID001",
                "exit_reason": "FUTURE_DEPENDENT" if last_date > decision else "HOLD",
                "exit_session": decision.date().isoformat(),
            }
        ]

    report = validate_lookahead(
        frame,
        decision_dates=[final_decisions(frame, 5)[0]],
        evaluator=CsmomSnapshotEvaluator(exit_evaluator=leaky_exit),
    )
    assert report.status is ValidationStatus.FAIL
    assert any(diff.section.value == "EXITS" for diff in report.differences)


def test_input_row_order_does_not_change_snapshot() -> None:
    frame = make_panel()
    decision = final_decisions(frame, 1)[0]
    evaluator = CsmomSnapshotEvaluator()
    first = evaluator(frame, decision)
    shuffled = evaluator(frame.sample(frac=1.0, random_state=9), decision)
    assert first.state_hash == shuffled.state_hash


def test_recursive_rejects_sub_minimum_warmup() -> None:
    frame = make_panel()
    with pytest.raises(ValidationContractError, match=">= 300"):
        validate_recursive_stability(
            frame,
            decision_dates=[final_decisions(frame, 1)[0]],
            warmup_sessions=(252, 300),
        )


def test_recursive_rejects_insufficient_history() -> None:
    frame = make_panel(sessions=330)
    with pytest.raises(ValidationContractError, match="360 required"):
        validate_recursive_stability(
            frame,
            decision_dates=[final_decisions(frame, 1)[0]],
            warmup_sessions=(300, 360),
        )


def test_missing_decision_date_is_rejected() -> None:
    with pytest.raises(ValidationContractError, match="absent"):
        validate_lookahead(make_panel(), decision_dates=["2035-01-01"])


def test_bias_suite_passes_clean_fixture_and_is_deterministically_hashed() -> None:
    frame = make_panel()
    at = datetime(2026, 8, 8, 22, 0, tzinfo=UTC)
    dates = final_decisions(frame, 1)
    first = validate_strategy_bias_suite(frame, decision_dates=dates, generated_at=at)
    second = validate_strategy_bias_suite(frame.sample(frac=1.0, random_state=12), decision_dates=dates, generated_at=at)
    assert first["status"] == "PASS"
    assert first["suite_hash"] == second["suite_hash"]



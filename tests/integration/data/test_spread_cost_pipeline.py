from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from trading_bot.data.contracts import DailyBar, DataQualityStatus
from trading_bot.data.costs import (
    NbboQuote,
    RegulatoryFeeScheduleEntry,
    SpreadCalibrationPoint,
    SpreadProxyObservation,
    TradeSide,
    TransactionCostAssumptions,
    build_spread_proxy,
    build_time_weighted_nbbo_spread,
    build_transaction_cost_input,
    fit_spread_calibration,
    passes_phase01_spread_gate,
)

UTC = timezone.utc
IID = UUID("00000000-0000-0000-0000-000000000011")


def dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, day, hour, minute, tzinfo=UTC)


def daily(day: int, high: str, low: str) -> DailyBar:
    return DailyBar(
        instrument_id=IID,
        session_date=date(2026, 1, day),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("100"),
        volume=2_000_000,
        observed_at=dt(day, 21),
        available_at=dt(day, 21, 30),
        snapshot_id=f"d-{day}",
        quality_status=DataQualityStatus.VALID,
    )


def historical_calibration() -> SpreadCalibrationPoint:
    proxy = SpreadProxyObservation(
        instrument_id=IID,
        session_date=date(2025, 12, 29),
        available_at=datetime(2025, 12, 29, 21, 30, tzinfo=UTC),
        raw_corwin_schultz_bps=Decimal("10"),
        adv60_usd=Decimal("30000000"),
        source_snapshot_ids=("historical-bars",),
    )
    start = datetime(2025, 12, 30, 15, 0, tzinfo=UTC)
    q = NbboQuote(
        instrument_id=IID,
        symbol="TEST",
        observed_at=start - timedelta(seconds=10),
        available_at=start - timedelta(seconds=9),
        bid_price=Decimal("99.9"),
        ask_price=Decimal("100.1"),
        bid_size=100,
        ask_size=100,
        source_snapshot_id="historical-quotes",
        sequence_number=1,
    )
    target = build_time_weighted_nbbo_spread(
        [q],
        session_date=date(2025, 12, 30),
        window_start=start,
        window_end=start + timedelta(minutes=30),
    )
    return SpreadCalibrationPoint(proxy=proxy, target=target)


def test_prior_close_spread_gate_then_execution_cost_is_separate() -> None:
    model = fit_spread_calibration(
        [historical_calibration()],
        decision_at=dt(5, 21, 30),
        minimum_observations_per_bucket=1,
    )
    proxy = build_spread_proxy(
        daily(4, "100.05", "99.95"),
        daily(5, "100.05", "99.95"),
        decision_at=dt(5, 21, 30),
        adv60_usd=Decimal("30000000"),
    )
    predicted = model.predict_bps(proxy, decision_at=dt(5, 21, 30))
    assert passes_phase01_spread_gate(predicted)

    schedule = RegulatoryFeeScheduleEntry(
        effective_from=date(2026, 1, 1),
        effective_to=None,
        sec_section31_per_million=Decimal("0"),
        finra_taf_per_share=Decimal("0.000195"),
        finra_taf_max_per_trade=Decimal("9.79"),
        source_reference="test schedule",
    )
    costs = build_transaction_cost_input(
        trade_date=date(2026, 1, 6),
        side=TradeSide.BUY,
        shares=8,
        benchmark_price=Decimal("101"),
        modeled_spread_bps=predicted,
        adv60_usd=Decimal("30000000"),
        schedule=schedule,
        assumptions=TransactionCostAssumptions(
            residual_slippage_bps=Decimal("2"),
            impact_floor_bps=Decimal("1"),
            impact_coefficient_bps=Decimal("100"),
            online_commission_usd=Decimal("0"),
        ),
    )
    assert costs.total_cost_usd > 0
    assert costs.modeled_spread_bps == predicted

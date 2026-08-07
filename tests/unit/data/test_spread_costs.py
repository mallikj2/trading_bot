from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.data.contracts import DailyBar, DataQualityStatus
from trading_bot.data.costs import (
    LiquidityBucket,
    NbboQuote,
    RegulatoryFeeScheduleEntry,
    SpreadCalibrationPoint,
    SpreadProxyObservation,
    TradeSide,
    TransactionCostAssumptions,
    build_spread_proxy,
    build_time_weighted_nbbo_spread,
    build_transaction_cost_input,
    corwin_schultz_spread_bps,
    fit_spread_calibration,
    liquidity_bucket,
    passes_phase01_spread_gate,
    regulatory_sell_fees_usd,
    select_fee_schedule,
)
from trading_bot.data.errors import DataContractError, PointInTimeError

UTC = timezone.utc
IID = UUID("00000000-0000-0000-0000-000000000001")


def dt(y: int, m: int, d: int, hh: int, mm: int, ss: int = 0) -> datetime:
    return datetime(y, m, d, hh, mm, ss, tzinfo=UTC)


def bar(day: int, *, high: str, low: str, available: datetime) -> DailyBar:
    return DailyBar(
        instrument_id=IID,
        session_date=date(2026, 1, day),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("100"),
        volume=1_000_000,
        observed_at=dt(2026, 1, day, 21, 0),
        available_at=available,
        snapshot_id=f"snap-{day}",
        quality_status=DataQualityStatus.VALID,
    )


def quote(at: datetime, bid: str, ask: str, seq: int) -> NbboQuote:
    return NbboQuote(
        instrument_id=IID,
        symbol="TEST",
        observed_at=at,
        available_at=at + timedelta(milliseconds=1),
        bid_price=Decimal(bid),
        ask_price=Decimal(ask),
        bid_size=100,
        ask_size=100,
        source_snapshot_id="quote-snap",
        sequence_number=seq,
    )


def test_liquidity_bucket_boundaries() -> None:
    assert liquidity_bucket(Decimal("25000000")) == LiquidityBucket.ADV_25_50M
    assert liquidity_bucket(Decimal("50000000")) == LiquidityBucket.ADV_50_100M
    assert liquidity_bucket(Decimal("100000000")) == LiquidityBucket.ADV_100_250M
    assert liquidity_bucket(Decimal("250000000")) == LiquidityBucket.ADV_250M_PLUS
    with pytest.raises(DataContractError):
        liquidity_bucket(Decimal("24999999"))


def test_nbbo_rejects_crossed_market() -> None:
    with pytest.raises(DataContractError):
        quote(dt(2026, 1, 5, 15, 0), "100.10", "100.00", 1)


def test_time_weighted_nbbo_spread_requires_start_state() -> None:
    start = dt(2026, 1, 5, 15, 0)
    end = dt(2026, 1, 5, 15, 30)
    with pytest.raises(DataContractError):
        build_time_weighted_nbbo_spread(
            [quote(start + timedelta(minutes=1), "100", "100.10", 1)],
            session_date=date(2026, 1, 5),
            window_start=start,
            window_end=end,
        )


def test_time_weighted_nbbo_spread_is_duration_weighted() -> None:
    start = dt(2026, 1, 5, 15, 0)
    end = dt(2026, 1, 5, 15, 30)
    q1 = quote(start - timedelta(seconds=30), "100", "100.10", 1)
    q2 = quote(start + timedelta(minutes=15), "100", "100.20", 2)
    result = build_time_weighted_nbbo_spread(
        [q1, q2],
        session_date=date(2026, 1, 5),
        window_start=start,
        window_end=end,
    )
    s1 = q1.quoted_spread_bps
    s2 = q2.quoted_spread_bps
    assert abs(result.time_weighted_spread_bps - ((s1 + s2) / Decimal("2"))) < Decimal("0.000001")
    assert result.covered_seconds == Decimal("1800.0")


def test_time_weighted_nbbo_rejects_stale_start() -> None:
    start = dt(2026, 1, 5, 15, 0)
    with pytest.raises(DataContractError):
        build_time_weighted_nbbo_spread(
            [quote(start - timedelta(seconds=61), "100", "100.10", 1)],
            session_date=date(2026, 1, 5),
            window_start=start,
            window_end=start + timedelta(minutes=30),
        )


def test_corwin_schultz_is_nonnegative_and_deterministic() -> None:
    b1 = bar(2, high="102", low="98", available=dt(2026, 1, 2, 21, 30))
    b2 = bar(3, high="103", low="99", available=dt(2026, 1, 3, 21, 30))
    result = corwin_schultz_spread_bps(b1, b2)
    assert result >= 0
    assert result == corwin_schultz_spread_bps(b1, b2)


def test_spread_proxy_blocks_future_bar() -> None:
    b1 = bar(2, high="102", low="98", available=dt(2026, 1, 2, 21, 30))
    b2 = bar(3, high="103", low="99", available=dt(2026, 1, 3, 22, 0))
    with pytest.raises(PointInTimeError):
        build_spread_proxy(
            b1,
            b2,
            decision_at=dt(2026, 1, 3, 21, 30),
            adv60_usd=Decimal("30000000"),
        )


def calibration_point(*, target_available: datetime, observed_bps: str = "12") -> SpreadCalibrationPoint:
    proxy = SpreadProxyObservation(
        instrument_id=IID,
        session_date=date(2026, 1, 2),
        available_at=dt(2026, 1, 2, 21, 30),
        raw_corwin_schultz_bps=Decimal("6"),
        adv60_usd=Decimal("30000000"),
        source_snapshot_ids=("daily",),
    )
    target = build_time_weighted_nbbo_spread(
        [quote(dt(2026, 1, 5, 14, 59, 30), "100", str(Decimal("100") + Decimal(observed_bps) / Decimal("100")), 1)],
        session_date=date(2026, 1, 5),
        window_start=dt(2026, 1, 5, 15, 0),
        window_end=dt(2026, 1, 5, 15, 30),
    )
    # The aggregation's SIP availability is not the point of this helper; replace it
    # with an explicit historical target availability for leakage tests.
    target = type(target)(
        instrument_id=target.instrument_id,
        symbol=target.symbol,
        session_date=target.session_date,
        window_start=target.window_start,
        window_end=target.window_end,
        time_weighted_spread_bps=Decimal(observed_bps),
        quote_count=target.quote_count,
        covered_seconds=target.covered_seconds,
        source_snapshot_ids=target.source_snapshot_ids,
        available_at=target_available,
    )
    return SpreadCalibrationPoint(proxy=proxy, target=target)


def test_spread_calibration_uses_only_known_targets() -> None:
    known = calibration_point(target_available=dt(2026, 1, 5, 15, 30), observed_bps="12")
    future = calibration_point(target_available=dt(2026, 2, 1, 15, 30), observed_bps="100")
    model = fit_spread_calibration(
        [known, future],
        decision_at=dt(2026, 1, 10, 21, 30),
        minimum_observations_per_bucket=1,
    )
    predicted = model.predict_bps(known.proxy, decision_at=dt(2026, 1, 10, 21, 30))
    assert predicted == Decimal("12")


def test_spread_model_blocks_missing_bucket() -> None:
    point = calibration_point(target_available=dt(2026, 1, 5, 15, 30))
    model = fit_spread_calibration(
        [point], decision_at=dt(2026, 1, 10, 21, 30), minimum_observations_per_bucket=1
    )
    other = SpreadProxyObservation(
        instrument_id=IID,
        session_date=date(2026, 1, 9),
        available_at=dt(2026, 1, 9, 21, 30),
        raw_corwin_schultz_bps=Decimal("5"),
        adv60_usd=Decimal("300000000"),
        source_snapshot_ids=("x",),
    )
    with pytest.raises(PointInTimeError):
        model.predict_bps(other, decision_at=dt(2026, 1, 10, 21, 30))


def test_phase01_spread_gate_is_inclusive_at_35_bps() -> None:
    assert passes_phase01_spread_gate(Decimal("35"))
    assert not passes_phase01_spread_gate(Decimal("35.0001"))


def fee_2026() -> RegulatoryFeeScheduleEntry:
    return RegulatoryFeeScheduleEntry(
        effective_from=date(2026, 4, 4),
        effective_to=None,
        sec_section31_per_million=Decimal("20.60"),
        finra_taf_per_share=Decimal("0.000195"),
        finra_taf_max_per_trade=Decimal("9.79"),
        source_reference="SEC-2026-2 + FINRA-2026",
    )


def test_regulatory_sell_fees_current_2026_example() -> None:
    fees = regulatory_sell_fees_usd(shares=100, price=Decimal("100"), schedule=fee_2026())
    assert fees == Decimal("0.225500")


def test_fee_schedule_fails_on_gap_or_overlap() -> None:
    entry = fee_2026()
    with pytest.raises(PointInTimeError):
        select_fee_schedule([entry], trade_date=date(2026, 4, 3))
    with pytest.raises(PointInTimeError):
        select_fee_schedule([entry, entry], trade_date=date(2026, 4, 4))


def test_buy_has_no_sell_regulatory_fee() -> None:
    result = build_transaction_cost_input(
        trade_date=date(2026, 4, 6),
        side=TradeSide.BUY,
        shares=10,
        benchmark_price=Decimal("100"),
        modeled_spread_bps=Decimal("10"),
        adv60_usd=Decimal("25000000"),
        schedule=fee_2026(),
        assumptions=TransactionCostAssumptions(residual_slippage_bps=Decimal("2"), impact_floor_bps=Decimal("1"), impact_coefficient_bps=Decimal("100"), online_commission_usd=Decimal("0")),
    )
    assert result.regulatory_fees_usd == 0
    assert result.half_spread_bps == Decimal("5")


def test_sell_includes_regulatory_fee_and_pessimistic_doubles() -> None:
    base = build_transaction_cost_input(
        trade_date=date(2026, 4, 6),
        side=TradeSide.SELL,
        shares=10,
        benchmark_price=Decimal("100"),
        modeled_spread_bps=Decimal("10"),
        adv60_usd=Decimal("25000000"),
        schedule=fee_2026(),
        assumptions=TransactionCostAssumptions(residual_slippage_bps=Decimal("2"), impact_floor_bps=Decimal("1"), impact_coefficient_bps=Decimal("100"), online_commission_usd=Decimal("0")),
    )
    stress = build_transaction_cost_input(
        trade_date=date(2026, 4, 6),
        side=TradeSide.SELL,
        shares=10,
        benchmark_price=Decimal("100"),
        modeled_spread_bps=Decimal("10"),
        adv60_usd=Decimal("25000000"),
        schedule=fee_2026(),
        assumptions=TransactionCostAssumptions(residual_slippage_bps=Decimal("2"), impact_floor_bps=Decimal("1"), impact_coefficient_bps=Decimal("100"), online_commission_usd=Decimal("0")),
        pessimistic=True,
    )
    assert base.regulatory_fees_usd > 0
    assert stress.total_cost_usd == base.total_cost_usd * Decimal("2")


def test_small_account_impact_floor_is_binding() -> None:
    result = build_transaction_cost_input(
        trade_date=date(2026, 4, 6),
        side=TradeSide.BUY,
        shares=10,
        benchmark_price=Decimal("100"),
        modeled_spread_bps=Decimal("10"),
        adv60_usd=Decimal("25000000"),
        schedule=fee_2026(),
        assumptions=TransactionCostAssumptions(residual_slippage_bps=Decimal("2"), impact_floor_bps=Decimal("1"), impact_coefficient_bps=Decimal("100"), online_commission_usd=Decimal("0")),
    )
    assert result.impact_bps == Decimal("1")

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from trading_bot.data.errors import DataContractError, PointInTimeError
from trading_bot.data.financing import (
    FinancingBalanceSnapshot,
    FinancingPolicy,
    FinancingRateKind,
    FinancingRateObservation,
    FinancingSourceKind,
    accrue_financing,
    latest_financing_rate_as_of,
)

UTC = timezone.utc


def ts(day: int, hour: int = 20) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=UTC)


def rate(kind, *, value="0.04", available=ts(3), revision=0, source=FinancingSourceKind.PUBLIC_REFERENCE):
    return FinancingRateObservation(
        rate_kind=kind,
        rate_date=date(2026, 8, 3),
        available_at=available,
        annual_rate=Decimal(value),
        day_count_basis=360,
        provider="synthetic",
        source_kind=source,
        source_snapshot_id=f"rate-{kind.value}-{revision}",
        revision=revision,
    )


def balance(**overrides):
    values = dict(
        session_date=date(2026, 8, 3),
        account_equity_usd=Decimal("5000"),
        long_market_value_usd=Decimal("2500"),
        short_market_value_usd=Decimal("2500"),
        free_cash_usd=Decimal("2500"),
        short_sale_collateral_usd=Decimal("2500"),
        settled_debit_usd=Decimal("0"),
    )
    values.update(overrides)
    return FinancingBalanceSnapshot(**values)


def test_primary_analysis_cash_credit_is_zero_and_short_proceeds_are_not_reused():
    result = accrue_financing(balance(), decision_at=ts(3, 21), calendar_days=1, policy=FinancingPolicy())
    assert result.free_cash_credit_usd == 0
    assert result.short_collateral_credit_usd == 0
    assert result.margin_debit_cost_usd == 0
    assert result.primary_net_financing_usd == 0


def test_policy_rejects_reuse_of_short_sale_proceeds():
    with pytest.raises(DataContractError):
        FinancingPolicy(short_sale_proceeds_reusable=True)


def test_no_margin_mandate_rejects_any_settled_debit():
    with pytest.raises(DataContractError, match="no-margin-borrowing"):
        accrue_financing(
            balance(settled_debit_usd=Decimal("10")),
            decision_at=ts(3, 21),
            calendar_days=1,
            policy=FinancingPolicy(),
        )


def test_margin_debit_requires_broker_specific_rate_when_explicitly_enabled():
    policy = FinancingPolicy(margin_borrowing_permitted=True)
    with pytest.raises(PointInTimeError):
        accrue_financing(
            balance(settled_debit_usd=Decimal("1000")),
            decision_at=ts(3, 21),
            calendar_days=1,
            policy=policy,
        )


def test_margin_debit_formula_and_two_x_stress_cost_only():
    debit_rate = rate(
        FinancingRateKind.MARGIN_DEBIT,
        value="0.12",
        source=FinancingSourceKind.BROKER_SPECIFIC,
    )
    result = accrue_financing(
        balance(settled_debit_usd=Decimal("1000")),
        decision_at=ts(3, 21),
        calendar_days=3,
        policy=FinancingPolicy(margin_borrowing_permitted=True),
        margin_debit_rate=debit_rate,
        pessimistic_cost_multiplier=Decimal("2"),
    )
    assert result.margin_debit_cost_usd == Decimal("1")
    assert result.stressed_margin_debit_cost_usd == Decimal("2")


def test_reference_cash_rate_is_attribution_only_in_primary_analysis():
    reference = rate(FinancingRateKind.CASH_REFERENCE, value="0.036")
    result = accrue_financing(
        balance(free_cash_usd=Decimal("1000")),
        decision_at=ts(3, 21),
        calendar_days=10,
        policy=FinancingPolicy(),
        benchmark_cash_rate=reference,
    )
    assert result.free_cash_credit_usd == 0
    assert result.benchmark_cash_income_usd == Decimal("1")
    assert result.cash_drag_vs_benchmark_usd == Decimal("1")
    assert result.primary_net_financing_usd == 0


def test_positive_cash_credit_requires_broker_specific_evidence():
    policy = FinancingPolicy(primary_cash_credit_rate_zero=False)
    with pytest.raises(DataContractError, match="broker-specific"):
        accrue_financing(
            balance(free_cash_usd=Decimal("1000")),
            decision_at=ts(3, 21),
            calendar_days=1,
            policy=policy,
            broker_cash_credit_rate=rate(FinancingRateKind.BROKER_CASH_CREDIT),
        )


def test_future_cash_rate_cannot_leak_backward():
    policy = FinancingPolicy(primary_cash_credit_rate_zero=False)
    future = rate(
        FinancingRateKind.BROKER_CASH_CREDIT,
        available=ts(5),
        source=FinancingSourceKind.BROKER_SPECIFIC,
    )
    with pytest.raises(PointInTimeError):
        accrue_financing(
            balance(free_cash_usd=Decimal("1000")),
            decision_at=ts(3, 21),
            calendar_days=1,
            policy=policy,
            broker_cash_credit_rate=future,
        )


def test_latest_rate_selects_only_known_revision():
    rows = [
        rate(FinancingRateKind.CASH_REFERENCE, value="0.03", revision=0),
        rate(FinancingRateKind.CASH_REFERENCE, value="0.05", available=ts(5), revision=1),
    ]
    selected = latest_financing_rate_as_of(
        rows,
        rate_kind=FinancingRateKind.CASH_REFERENCE,
        rate_date=date(2026, 8, 3),
        decision_at=ts(3, 21),
    )
    assert selected is rows[0]


def test_gross_leverage_above_one_is_blocked_by_mandate_policy():
    over = balance(long_market_value_usd=Decimal("3000"), short_market_value_usd=Decimal("2500"))
    with pytest.raises(DataContractError, match="gross leverage"):
        accrue_financing(over, decision_at=ts(3, 21), calendar_days=1, policy=FinancingPolicy())

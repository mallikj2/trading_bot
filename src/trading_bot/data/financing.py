"""Point-in-time financing and cash-carry contracts for Phase 02.

The primary CSMOM-LS-v0.2 analysis is deliberately conservative: free cash earns
zero and short-sale proceeds are restricted collateral.  This module therefore
separates (a) the binding primary-analysis accounting from (b) optional financing
attribution and broker-specific debit charges.  It never treats short proceeds as
free leverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Sequence

from .errors import DataContractError, PointInTimeError
from .time_utils import require_aware


class FinancingRateKind(str, Enum):
    CASH_REFERENCE = "CASH_REFERENCE"
    BROKER_CASH_CREDIT = "BROKER_CASH_CREDIT"
    MARGIN_DEBIT = "MARGIN_DEBIT"


class FinancingSourceKind(str, Enum):
    PUBLIC_REFERENCE = "PUBLIC_REFERENCE"
    BROKER_SPECIFIC = "BROKER_SPECIFIC"
    PREREGISTERED_STRESS = "PREREGISTERED_STRESS"


@dataclass(frozen=True, slots=True)
class FinancingRateObservation:
    rate_kind: FinancingRateKind
    rate_date: date
    available_at: datetime
    annual_rate: Decimal
    day_count_basis: int
    provider: str
    source_kind: FinancingSourceKind
    source_snapshot_id: str
    revision: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "available_at", require_aware(self.available_at, "available_at"))
        if self.annual_rate < 0:
            raise DataContractError("financing annual_rate cannot be negative")
        if self.day_count_basis not in (360, 365, 366):
            raise DataContractError("unsupported financing day_count_basis")
        if not self.provider.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("financing provider and source_snapshot_id are required")
        if self.revision < 0:
            raise DataContractError("financing revision cannot be negative")


@dataclass(frozen=True, slots=True)
class FinancingBalanceSnapshot:
    session_date: date
    account_equity_usd: Decimal
    long_market_value_usd: Decimal
    short_market_value_usd: Decimal
    free_cash_usd: Decimal
    short_sale_collateral_usd: Decimal
    settled_debit_usd: Decimal

    def __post_init__(self) -> None:
        fields = (
            self.account_equity_usd,
            self.long_market_value_usd,
            self.short_market_value_usd,
            self.free_cash_usd,
            self.short_sale_collateral_usd,
            self.settled_debit_usd,
        )
        if any(value < 0 for value in fields):
            raise DataContractError("financing balances cannot be negative")
        if self.account_equity_usd <= 0:
            raise DataContractError("account_equity_usd must be positive")

    @property
    def gross_exposure_usd(self) -> Decimal:
        return self.long_market_value_usd + self.short_market_value_usd

    @property
    def net_exposure_usd(self) -> Decimal:
        return self.long_market_value_usd - self.short_market_value_usd

    @property
    def gross_leverage(self) -> Decimal:
        return self.gross_exposure_usd / self.account_equity_usd


@dataclass(frozen=True, slots=True)
class FinancingPolicy:
    primary_cash_credit_rate_zero: bool = True
    short_sale_proceeds_reusable: bool = False
    short_sale_collateral_earns_credit: bool = False
    margin_borrowing_permitted: bool = False
    maximum_gross_leverage: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if self.maximum_gross_leverage <= 0:
            raise DataContractError("maximum_gross_leverage must be positive")
        if self.short_sale_proceeds_reusable:
            raise DataContractError(
                "Phase 02 policy prohibits treating short-sale proceeds as reusable free cash"
            )


@dataclass(frozen=True, slots=True)
class FinancingAccrual:
    session_date: date
    calendar_days: int
    free_cash_credit_usd: Decimal
    short_collateral_credit_usd: Decimal
    margin_debit_cost_usd: Decimal
    stressed_margin_debit_cost_usd: Decimal
    benchmark_cash_income_usd: Decimal
    cash_drag_vs_benchmark_usd: Decimal
    source_snapshot_ids: tuple[str, ...]

    @property
    def primary_net_financing_usd(self) -> Decimal:
        """Binding Phase 01 financing contribution to the primary return series."""
        return self.free_cash_credit_usd + self.short_collateral_credit_usd - self.margin_debit_cost_usd

    @property
    def stressed_net_financing_usd(self) -> Decimal:
        return self.free_cash_credit_usd + self.short_collateral_credit_usd - self.stressed_margin_debit_cost_usd


def latest_financing_rate_as_of(
    observations: Sequence[FinancingRateObservation],
    *,
    rate_kind: FinancingRateKind,
    rate_date: date,
    decision_at: datetime,
) -> FinancingRateObservation | None:
    """Select the latest known revision for a rate date without future leakage."""

    decision = require_aware(decision_at, "decision_at")
    rows = [
        row
        for row in observations
        if row.rate_kind == rate_kind and row.rate_date == rate_date and row.available_at <= decision
    ]
    if not rows:
        return None
    contexts = {(row.provider, row.source_kind, row.day_count_basis) for row in rows}
    if len(contexts) > 1:
        raise DataContractError("financing rate observations mix incompatible contexts")
    key = max((row.available_at, row.revision) for row in rows)
    winners = [row for row in rows if (row.available_at, row.revision) == key]
    if len(winners) != 1:
        raise PointInTimeError("ambiguous financing rate revision")
    return winners[0]


def _interest(balance: Decimal, rate: FinancingRateObservation, calendar_days: int) -> Decimal:
    if calendar_days <= 0:
        raise DataContractError("calendar_days must be positive")
    return balance * rate.annual_rate * Decimal(calendar_days) / Decimal(rate.day_count_basis)


def accrue_financing(
    balance: FinancingBalanceSnapshot,
    *,
    decision_at: datetime,
    calendar_days: int,
    policy: FinancingPolicy,
    benchmark_cash_rate: FinancingRateObservation | None = None,
    broker_cash_credit_rate: FinancingRateObservation | None = None,
    margin_debit_rate: FinancingRateObservation | None = None,
    pessimistic_cost_multiplier: Decimal = Decimal("2"),
) -> FinancingAccrual:
    """Accrue one financing interval under explicit, fail-closed assumptions.

    - Primary cash credit is zero when ``primary_cash_credit_rate_zero`` is set.
    - Short-sale collateral is not free cash and earns zero unless an explicit
      broker-specific policy and rate are supplied.
    - Any settled debit is prohibited under the mandate unless margin borrowing
      is explicitly enabled; if enabled, a broker-specific debit rate is required.
    - The Phase 01 pessimistic multiplier applies to financing *costs*, not to
      positive cash income.
    """

    decision = require_aware(decision_at, "decision_at")
    if pessimistic_cost_multiplier < 1:
        raise DataContractError("pessimistic_cost_multiplier must be >= 1")
    if balance.gross_leverage > policy.maximum_gross_leverage:
        raise DataContractError("gross leverage exceeds financing policy")

    source_ids: set[str] = set()

    free_credit = Decimal("0")
    if not policy.primary_cash_credit_rate_zero and balance.free_cash_usd > 0:
        if broker_cash_credit_rate is None:
            raise PointInTimeError("broker cash credit rate required when positive cash carry is enabled")
        if broker_cash_credit_rate.rate_kind != FinancingRateKind.BROKER_CASH_CREDIT:
            raise DataContractError("wrong rate kind for broker cash credit")
        if broker_cash_credit_rate.available_at > decision:
            raise PointInTimeError("broker cash credit rate unavailable at decision time")
        if broker_cash_credit_rate.source_kind != FinancingSourceKind.BROKER_SPECIFIC:
            raise DataContractError("cash credit requires broker-specific evidence")
        free_credit = _interest(balance.free_cash_usd, broker_cash_credit_rate, calendar_days)
        source_ids.add(broker_cash_credit_rate.source_snapshot_id)

    collateral_credit = Decimal("0")
    if policy.short_sale_collateral_earns_credit and balance.short_sale_collateral_usd > 0:
        if broker_cash_credit_rate is None:
            raise PointInTimeError("broker-specific credit rate required for short collateral")
        if broker_cash_credit_rate.source_kind != FinancingSourceKind.BROKER_SPECIFIC:
            raise DataContractError("short collateral credit requires broker-specific evidence")
        if broker_cash_credit_rate.available_at > decision:
            raise PointInTimeError("short collateral credit rate unavailable at decision time")
        collateral_credit = _interest(balance.short_sale_collateral_usd, broker_cash_credit_rate, calendar_days)
        source_ids.add(broker_cash_credit_rate.source_snapshot_id)

    debit_cost = Decimal("0")
    if balance.settled_debit_usd > 0:
        if not policy.margin_borrowing_permitted:
            raise DataContractError("settled debit violates no-margin-borrowing mandate")
        if margin_debit_rate is None:
            raise PointInTimeError("margin debit rate required for positive settled debit")
        if margin_debit_rate.rate_kind != FinancingRateKind.MARGIN_DEBIT:
            raise DataContractError("wrong rate kind for margin debit")
        if margin_debit_rate.source_kind != FinancingSourceKind.BROKER_SPECIFIC:
            raise DataContractError("margin debit requires broker-specific rate evidence")
        if margin_debit_rate.available_at > decision:
            raise PointInTimeError("margin debit rate unavailable at decision time")
        debit_cost = _interest(balance.settled_debit_usd, margin_debit_rate, calendar_days)
        source_ids.add(margin_debit_rate.source_snapshot_id)

    benchmark_income = Decimal("0")
    if benchmark_cash_rate is not None and balance.free_cash_usd > 0:
        if benchmark_cash_rate.rate_kind != FinancingRateKind.CASH_REFERENCE:
            raise DataContractError("wrong rate kind for cash benchmark")
        if benchmark_cash_rate.available_at > decision:
            raise PointInTimeError("cash benchmark rate unavailable at decision time")
        benchmark_income = _interest(balance.free_cash_usd, benchmark_cash_rate, calendar_days)
        source_ids.add(benchmark_cash_rate.source_snapshot_id)

    return FinancingAccrual(
        session_date=balance.session_date,
        calendar_days=calendar_days,
        free_cash_credit_usd=free_credit,
        short_collateral_credit_usd=collateral_credit,
        margin_debit_cost_usd=debit_cost,
        stressed_margin_debit_cost_usd=debit_cost * pessimistic_cost_multiplier,
        benchmark_cash_income_usd=benchmark_income,
        cash_drag_vs_benchmark_usd=benchmark_income - free_credit,
        source_snapshot_ids=tuple(sorted(source_ids)),
    )

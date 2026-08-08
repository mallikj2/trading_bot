"""Point-in-time spread calibration and transaction-cost inputs for Phase 02.

The module deliberately separates three concepts:
1. observed historical NBBO spread used only as a calibration/validation target;
2. a pre-trade spread estimate that must be knowable at the strategy decision time;
3. realized/modelled transaction costs applied to the approved VWAP fill benchmark.

Future execution-window quotes must never be used directly by the prior-close do-not-trade rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from math import exp, log, sqrt
from statistics import median
from typing import Iterable, Mapping, Sequence
from uuid import UUID

from .contracts import DailyBar, DataQualityStatus
from .errors import DataContractError, PointInTimeError
from .time_utils import require_aware

BPS = Decimal("10000")
ONE_MILLION = Decimal("1000000")


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class LiquidityBucket(str, Enum):
    ADV_25_50M = "ADV_25_50M"
    ADV_50_100M = "ADV_50_100M"
    ADV_100_250M = "ADV_100_250M"
    ADV_250M_PLUS = "ADV_250M_PLUS"


def liquidity_bucket(adv60_usd: Decimal) -> LiquidityBucket:
    if adv60_usd < Decimal("25000000"):
        raise DataContractError("spread calibration requires Phase 01 ADV60 >= USD 25M")
    if adv60_usd < Decimal("50000000"):
        return LiquidityBucket.ADV_25_50M
    if adv60_usd < Decimal("100000000"):
        return LiquidityBucket.ADV_50_100M
    if adv60_usd < Decimal("250000000"):
        return LiquidityBucket.ADV_100_250M
    return LiquidityBucket.ADV_250M_PLUS


@dataclass(frozen=True, slots=True)
class NbboQuote:
    instrument_id: UUID
    symbol: str
    observed_at: datetime
    available_at: datetime
    bid_price: Decimal
    ask_price: Decimal
    bid_size: int
    ask_size: int
    source_snapshot_id: str
    sequence_number: int | None = None
    quality_status: DataQualityStatus = DataQualityStatus.VALID

    def __post_init__(self) -> None:
        observed = require_aware(self.observed_at, "observed_at")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "available_at", available)
        if available < observed:
            raise DataContractError("quote available_at cannot precede observed_at")
        if not self.symbol.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("quote symbol and source_snapshot_id are required")
        if self.bid_price <= 0 or self.ask_price <= 0:
            raise DataContractError("NBBO bid and ask must be positive")
        if self.ask_price < self.bid_price:
            raise DataContractError("crossed NBBO is not a valid calibration quote")
        if self.bid_size < 0 or self.ask_size < 0:
            raise DataContractError("NBBO sizes cannot be negative")
        if self.sequence_number is not None and self.sequence_number < 0:
            raise DataContractError("sequence_number cannot be negative")

    @property
    def midpoint(self) -> Decimal:
        return (self.bid_price + self.ask_price) / Decimal("2")

    @property
    def quoted_spread_bps(self) -> Decimal:
        return (self.ask_price - self.bid_price) / self.midpoint * BPS


@dataclass(frozen=True, slots=True)
class ObservedSpreadWindow:
    instrument_id: UUID
    symbol: str
    session_date: date
    window_start: datetime
    window_end: datetime
    time_weighted_spread_bps: Decimal
    quote_count: int
    covered_seconds: Decimal
    source_snapshot_ids: tuple[str, ...]
    available_at: datetime

    def __post_init__(self) -> None:
        start = require_aware(self.window_start, "window_start")
        end = require_aware(self.window_end, "window_end")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "window_start", start)
        object.__setattr__(self, "window_end", end)
        object.__setattr__(self, "available_at", available)
        if end <= start:
            raise DataContractError("spread window must have positive duration")
        if self.time_weighted_spread_bps < 0:
            raise DataContractError("spread cannot be negative")
        if self.quote_count < 1 or self.covered_seconds <= 0:
            raise DataContractError("observed spread window requires quote coverage")


def build_time_weighted_nbbo_spread(
    quotes: Iterable[NbboQuote],
    *,
    session_date: date,
    window_start: datetime,
    window_end: datetime,
    max_initial_quote_age: timedelta = timedelta(seconds=60),
) -> ObservedSpreadWindow:
    """Build a time-weighted quoted spread over a fixed execution window.

    At least one valid quote at or before the window start is required so the
    prevailing NBBO is known at the first instant.  Quotes after the window are
    ignored. Crossed/invalid/stale-start observations fail closed.
    """

    start = require_aware(window_start, "window_start")
    end = require_aware(window_end, "window_end")
    if end <= start:
        raise ValueError("window_end must be later than window_start")
    if max_initial_quote_age < timedelta(0):
        raise ValueError("max_initial_quote_age cannot be negative")

    rows = sorted(quotes, key=lambda q: (q.observed_at, q.sequence_number or -1))
    if not rows:
        raise DataContractError("NBBO calibration input is empty")
    identities = {(q.instrument_id, q.symbol) for q in rows}
    if len(identities) != 1:
        raise DataContractError("NBBO window must reference one instrument and symbol")
    if any(q.quality_status != DataQualityStatus.VALID for q in rows):
        raise DataContractError("NBBO window contains non-valid quotes")

    prior = [q for q in rows if q.observed_at <= start]
    if not prior:
        raise DataContractError("no prevailing NBBO exists at execution-window start")
    state = prior[-1]
    if start - state.observed_at > max_initial_quote_age:
        raise DataContractError("prevailing NBBO at window start is too stale")

    updates = [q for q in rows if start < q.observed_at < end]
    timeline = [state, *updates]
    weighted = Decimal("0")
    covered = Decimal("0")
    for index, quote in enumerate(timeline):
        interval_start = start if index == 0 else quote.observed_at
        interval_end = end if index + 1 == len(timeline) else timeline[index + 1].observed_at
        if interval_end <= interval_start:
            continue
        seconds = Decimal(str((interval_end - interval_start).total_seconds()))
        weighted += quote.quoted_spread_bps * seconds
        covered += seconds

    expected_seconds = Decimal(str((end - start).total_seconds()))
    if covered != expected_seconds:
        raise DataContractError("NBBO window does not provide continuous state coverage")

    first = rows[0]
    all_used = timeline
    available_at = max(q.available_at for q in all_used)
    return ObservedSpreadWindow(
        instrument_id=first.instrument_id,
        symbol=first.symbol,
        session_date=session_date,
        window_start=start,
        window_end=end,
        time_weighted_spread_bps=weighted / covered,
        quote_count=len(all_used),
        covered_seconds=covered,
        source_snapshot_ids=tuple(sorted({q.source_snapshot_id for q in all_used})),
        available_at=available_at,
    )


@dataclass(frozen=True, slots=True)
class SpreadProxyObservation:
    instrument_id: UUID
    session_date: date
    available_at: datetime
    raw_corwin_schultz_bps: Decimal
    adv60_usd: Decimal
    source_snapshot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "available_at", available)
        if self.raw_corwin_schultz_bps < 0:
            raise DataContractError("raw spread proxy cannot be negative")
        liquidity_bucket(self.adv60_usd)
        if not self.source_snapshot_ids:
            raise DataContractError("spread proxy requires source lineage")


def corwin_schultz_spread_bps(previous_bar: DailyBar, current_bar: DailyBar) -> Decimal:
    """Return the non-negative Corwin-Schultz high-low spread estimate in bps.

    Uses only two completed daily bars. Both must be valid, ordered, and refer to
    the same instrument. The formula follows Corwin & Schultz (2012).
    """

    if previous_bar.instrument_id != current_bar.instrument_id:
        raise DataContractError("Corwin-Schultz bars must reference one instrument")
    if previous_bar.session_date >= current_bar.session_date:
        raise DataContractError("Corwin-Schultz bars must be in chronological order")
    if previous_bar.quality_status != DataQualityStatus.VALID or current_bar.quality_status != DataQualityStatus.VALID:
        raise DataContractError("Corwin-Schultz requires valid daily bars")

    h1, l1 = float(previous_bar.high), float(previous_bar.low)
    h2, l2 = float(current_bar.high), float(current_bar.low)
    beta = log(h1 / l1) ** 2 + log(h2 / l2) ** 2
    two_day_high = max(h1, h2)
    two_day_low = min(l1, l2)
    gamma = log(two_day_high / two_day_low) ** 2
    denominator = 3.0 - 2.0 * sqrt(2.0)
    alpha = (sqrt(2.0 * beta) - sqrt(beta)) / denominator - sqrt(gamma / denominator)
    alpha = max(alpha, 0.0)
    spread_fraction = 2.0 * (exp(alpha) - 1.0) / (1.0 + exp(alpha))
    return Decimal(str(spread_fraction * 10000.0))


def build_spread_proxy(
    previous_bar: DailyBar,
    current_bar: DailyBar,
    *,
    decision_at: datetime,
    adv60_usd: Decimal,
) -> SpreadProxyObservation:
    decision = require_aware(decision_at, "decision_at")
    if previous_bar.available_at > decision or current_bar.available_at > decision:
        raise PointInTimeError("spread proxy attempted to use a bar unavailable at decision time")
    return SpreadProxyObservation(
        instrument_id=current_bar.instrument_id,
        session_date=current_bar.session_date,
        available_at=max(previous_bar.available_at, current_bar.available_at),
        raw_corwin_schultz_bps=corwin_schultz_spread_bps(previous_bar, current_bar),
        adv60_usd=adv60_usd,
        source_snapshot_ids=tuple(sorted({previous_bar.snapshot_id, current_bar.snapshot_id})),
    )


@dataclass(frozen=True, slots=True)
class SpreadCalibrationPoint:
    proxy: SpreadProxyObservation
    target: ObservedSpreadWindow

    def __post_init__(self) -> None:
        if self.proxy.instrument_id != self.target.instrument_id:
            raise DataContractError("calibration point instrument mismatch")
        if self.target.session_date <= self.proxy.session_date:
            raise DataContractError("calibration target must be a later execution session")


@dataclass(frozen=True, slots=True)
class BucketCalibration:
    bucket: LiquidityBucket
    observation_count: int
    median_ratio: Decimal
    median_observed_bps: Decimal


@dataclass(frozen=True, slots=True)
class SpreadCalibrationModel:
    fit_at: datetime
    proxy_floor_bps: Decimal
    maximum_model_spread_bps: Decimal
    buckets: Mapping[LiquidityBucket, BucketCalibration]

    def __post_init__(self) -> None:
        object.__setattr__(self, "fit_at", require_aware(self.fit_at, "fit_at"))
        if self.proxy_floor_bps <= 0:
            raise DataContractError("proxy_floor_bps must be positive")
        if self.maximum_model_spread_bps <= self.proxy_floor_bps:
            raise DataContractError("maximum model spread must exceed proxy floor")

    def predict_bps(self, proxy: SpreadProxyObservation, *, decision_at: datetime) -> Decimal:
        decision = require_aware(decision_at, "decision_at")
        if self.fit_at > decision:
            raise PointInTimeError("spread calibration model was fit after the decision time")
        if proxy.available_at > decision:
            raise PointInTimeError("spread proxy was unavailable at decision time")
        bucket = liquidity_bucket(proxy.adv60_usd)
        calibration = self.buckets.get(bucket)
        if calibration is None:
            raise PointInTimeError(f"no historical spread calibration for liquidity bucket {bucket.value}")
        raw = max(proxy.raw_corwin_schultz_bps, self.proxy_floor_bps)
        calibrated = max(calibration.median_observed_bps, raw * calibration.median_ratio)
        return min(calibrated, self.maximum_model_spread_bps)


def fit_spread_calibration(
    points: Sequence[SpreadCalibrationPoint],
    *,
    decision_at: datetime,
    minimum_observations_per_bucket: int = 60,
    proxy_floor_bps: Decimal = Decimal("1"),
    maximum_model_spread_bps: Decimal = Decimal("100"),
) -> SpreadCalibrationModel:
    """Fit a robust expanding calibration using only targets known before decision_at."""

    decision = require_aware(decision_at, "decision_at")
    if minimum_observations_per_bucket < 1:
        raise ValueError("minimum_observations_per_bucket must be positive")
    if proxy_floor_bps <= 0:
        raise ValueError("proxy_floor_bps must be positive")

    grouped: dict[LiquidityBucket, list[SpreadCalibrationPoint]] = {bucket: [] for bucket in LiquidityBucket}
    for point in points:
        if point.proxy.available_at > decision or point.target.available_at > decision:
            continue
        bucket = liquidity_bucket(point.proxy.adv60_usd)
        grouped[bucket].append(point)

    fitted: dict[LiquidityBucket, BucketCalibration] = {}
    for bucket, rows in grouped.items():
        if len(rows) < minimum_observations_per_bucket:
            continue
        ratios: list[Decimal] = []
        observed: list[Decimal] = []
        for point in rows:
            x = max(point.proxy.raw_corwin_schultz_bps, proxy_floor_bps)
            y = point.target.time_weighted_spread_bps
            if y < 0:
                raise DataContractError("observed calibration spread cannot be negative")
            ratios.append(y / x)
            observed.append(y)
        fitted[bucket] = BucketCalibration(
            bucket=bucket,
            observation_count=len(rows),
            median_ratio=Decimal(str(median(ratios))),
            median_observed_bps=Decimal(str(median(observed))),
        )

    if not fitted:
        raise PointInTimeError("insufficient historical quote evidence to fit any spread bucket")
    return SpreadCalibrationModel(
        fit_at=decision,
        proxy_floor_bps=proxy_floor_bps,
        maximum_model_spread_bps=maximum_model_spread_bps,
        buckets=fitted,
    )


def passes_phase01_spread_gate(
    modeled_spread_bps: Decimal, *, maximum_spread_bps: Decimal = Decimal("35")
) -> bool:
    if modeled_spread_bps < 0 or maximum_spread_bps <= 0:
        raise DataContractError("spread gate inputs are invalid")
    return modeled_spread_bps <= maximum_spread_bps


@dataclass(frozen=True, slots=True)
class RegulatoryFeeScheduleEntry:
    effective_from: date
    effective_to: date | None
    sec_section31_per_million: Decimal
    finra_taf_per_share: Decimal
    finra_taf_max_per_trade: Decimal
    source_reference: str

    def __post_init__(self) -> None:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise DataContractError("fee schedule end precedes start")
        if self.sec_section31_per_million < 0 or self.finra_taf_per_share < 0 or self.finra_taf_max_per_trade < 0:
            raise DataContractError("regulatory fee rates cannot be negative")
        if not self.source_reference.strip():
            raise DataContractError("fee schedule source_reference is required")

    def covers(self, trade_date: date) -> bool:
        return self.effective_from <= trade_date and (self.effective_to is None or trade_date <= self.effective_to)


def select_fee_schedule(
    entries: Sequence[RegulatoryFeeScheduleEntry], *, trade_date: date
) -> RegulatoryFeeScheduleEntry:
    matching = [entry for entry in entries if entry.covers(trade_date)]
    if len(matching) != 1:
        raise PointInTimeError(f"regulatory fee schedule coverage is ambiguous or missing for {trade_date}")
    return matching[0]


def regulatory_sell_fees_usd(
    *,
    shares: int,
    price: Decimal,
    schedule: RegulatoryFeeScheduleEntry,
) -> Decimal:
    if shares <= 0 or price <= 0:
        raise DataContractError("shares and price must be positive")
    notional = Decimal(shares) * price
    section31 = notional * schedule.sec_section31_per_million / ONE_MILLION
    # FINRA Schedule A provides that no TAF is assessed when the execution
    # price is below the per-share TAF rate.  The Phase 01 universe has a
    # much higher price floor, but the data kernel still models the rule.
    taf = Decimal("0")
    if price >= schedule.finra_taf_per_share:
        taf = min(Decimal(shares) * schedule.finra_taf_per_share, schedule.finra_taf_max_per_trade)
    return section31 + taf


@dataclass(frozen=True, slots=True)
class TransactionCostAssumptions:
    residual_slippage_bps: Decimal
    impact_floor_bps: Decimal
    impact_coefficient_bps: Decimal
    online_commission_usd: Decimal
    pessimistic_multiplier: Decimal = Decimal("2")

    def __post_init__(self) -> None:
        values = (
            self.residual_slippage_bps,
            self.impact_floor_bps,
            self.impact_coefficient_bps,
            self.online_commission_usd,
        )
        if any(value < 0 for value in values):
            raise DataContractError("transaction-cost assumptions cannot be negative")
        if self.pessimistic_multiplier < 1:
            raise DataContractError("pessimistic multiplier must be at least 1")


def market_impact_bps(
    *, order_notional_usd: Decimal, adv60_usd: Decimal, assumptions: TransactionCostAssumptions
) -> Decimal:
    if order_notional_usd <= 0 or adv60_usd <= 0:
        raise DataContractError("order notional and ADV60 must be positive")
    participation = float(order_notional_usd / adv60_usd)
    modeled = assumptions.impact_coefficient_bps * Decimal(str(sqrt(participation)))
    return max(assumptions.impact_floor_bps, modeled)


@dataclass(frozen=True, slots=True)
class TransactionCostInput:
    trade_date: date
    side: TradeSide
    shares: int
    benchmark_price: Decimal
    modeled_spread_bps: Decimal
    half_spread_bps: Decimal
    residual_slippage_bps: Decimal
    impact_bps: Decimal
    commission_usd: Decimal
    regulatory_fees_usd: Decimal
    total_cost_usd: Decimal
    all_in_cost_bps: Decimal
    scenario_multiplier: Decimal


def build_transaction_cost_input(
    *,
    trade_date: date,
    side: TradeSide,
    shares: int,
    benchmark_price: Decimal,
    modeled_spread_bps: Decimal,
    adv60_usd: Decimal,
    schedule: RegulatoryFeeScheduleEntry,
    assumptions: TransactionCostAssumptions,
    pessimistic: bool = False,
) -> TransactionCostInput:
    if shares <= 0 or benchmark_price <= 0 or modeled_spread_bps < 0:
        raise DataContractError("invalid transaction-cost inputs")
    notional = Decimal(shares) * benchmark_price
    multiplier = assumptions.pessimistic_multiplier if pessimistic else Decimal("1")
    half_spread = modeled_spread_bps / Decimal("2")
    impact = market_impact_bps(
        order_notional_usd=notional,
        adv60_usd=adv60_usd,
        assumptions=assumptions,
    )
    variable_bps = (half_spread + assumptions.residual_slippage_bps + impact) * multiplier
    variable_usd = notional * variable_bps / BPS
    commission = assumptions.online_commission_usd * multiplier
    regulatory = Decimal("0")
    if side == TradeSide.SELL:
        regulatory = regulatory_sell_fees_usd(shares=shares, price=benchmark_price, schedule=schedule) * multiplier
    total = variable_usd + commission + regulatory
    all_in_bps = total / notional * BPS
    return TransactionCostInput(
        trade_date=trade_date,
        side=side,
        shares=shares,
        benchmark_price=benchmark_price,
        modeled_spread_bps=modeled_spread_bps,
        half_spread_bps=half_spread * multiplier,
        residual_slippage_bps=assumptions.residual_slippage_bps * multiplier,
        impact_bps=impact * multiplier,
        commission_usd=commission,
        regulatory_fees_usd=regulatory,
        total_cost_usd=total,
        all_in_cost_bps=all_in_bps,
        scenario_multiplier=multiplier,
    )


def adverse_fill_price(*, benchmark_price: Decimal, side: TradeSide, variable_cost_bps: Decimal) -> Decimal:
    """Apply spread/slippage/impact around the strategy's VWAP benchmark.

    Regulatory fees and commissions are cash charges and are intentionally not
    embedded in price.
    """

    if benchmark_price <= 0 or variable_cost_bps < 0:
        raise DataContractError("invalid adverse-fill inputs")
    adjustment = variable_cost_bps / BPS
    if side == TradeSide.BUY:
        return benchmark_price * (Decimal("1") + adjustment)
    return benchmark_price * (Decimal("1") - adjustment)

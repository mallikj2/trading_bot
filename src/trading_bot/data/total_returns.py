"""Point-in-time corporate-action and total-return processing.

The engine deliberately separates:

* raw tradable prices;
* split-adjusted prices used for price eligibility; and
* total-return-adjusted prices / forward total-return indices used for
  return, momentum, volatility, trend, benchmark, and attribution work.

Every build is performed as of a decision timestamp. Corporate-action and
valuation revisions not available at that timestamp are invisible. Incomplete
coverage or economically unresolved actions fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Iterable, Mapping
from uuid import UUID
from zoneinfo import ZoneInfo

from .contracts import (
    CorporateAction,
    CorporateActionStatus,
    CorporateActionType,
    DailyBar,
    DataQualityStatus,
)
from .errors import DataContractError, PointInTimeError
from .hashing import content_hash
from .time_utils import require_aware


NEW_YORK = ZoneInfo("America/New_York")
ONE = Decimal("1")
ZERO = Decimal("0")


class ActionValuationPurpose(str, Enum):
    DISTRIBUTION = "DISTRIBUTION"
    TERMINAL_CONSIDERATION = "TERMINAL_CONSIDERATION"


class ActionValuationMethod(str, Enum):
    OBSERVED_CHILD_CLOSE = "OBSERVED_CHILD_CLOSE"
    OBSERVED_SUCCESSOR_CLOSE = "OBSERVED_SUCCESSOR_CLOSE"
    PROVIDER_EXPLICIT_VALUE = "PROVIDER_EXPLICIT_VALUE"
    CASH_EQUIVALENT = "CASH_EQUIVALENT"
    ZERO_RECOVERY = "ZERO_RECOVERY"


CONTINUING_ECONOMIC_TYPES = frozenset(
    {
        CorporateActionType.SPLIT,
        CorporateActionType.REVERSE_SPLIT,
        CorporateActionType.CASH_DIVIDEND,
        CorporateActionType.STOCK_DIVIDEND,
        CorporateActionType.SPINOFF,
    }
)
TERMINAL_ECONOMIC_TYPES = frozenset(
    {
        CorporateActionType.MERGER,
        CorporateActionType.ACQUISITION,
        CorporateActionType.DELISTING,
        CorporateActionType.LIQUIDATION,
        CorporateActionType.BANKRUPTCY,
    }
)
NON_ECONOMIC_TYPES = frozenset(
    {CorporateActionType.SYMBOL_CHANGE, CorporateActionType.RELISTING}
)
UNSUPPORTED_MATERIAL_TYPES = frozenset(
    {CorporateActionType.TENDER_OFFER, CorporateActionType.RIGHTS_DISTRIBUTION}
)
DEFAULT_REQUIRED_COVERAGE_TYPES = frozenset(
    CONTINUING_ECONOMIC_TYPES
    | TERMINAL_ECONOMIC_TYPES
    | UNSUPPORTED_MATERIAL_TYPES
    | {CorporateActionType.SYMBOL_CHANGE}
)




def continuing_event_value(
    *,
    ex_close: Decimal,
    share_multiplier: Decimal = ONE,
    cash_per_old_share: Decimal = ZERO,
    noncash_value_per_old_share: Decimal = ZERO,
) -> Decimal:
    """Return ending economic value per old share for a continuing event."""
    if ex_close <= ZERO:
        raise DataContractError("ex_close must be positive")
    if share_multiplier <= ZERO:
        raise DataContractError("share_multiplier must be positive")
    if cash_per_old_share < ZERO or noncash_value_per_old_share < ZERO:
        raise DataContractError("distribution values cannot be negative")
    return (
        ex_close * share_multiplier
        + cash_per_old_share
        + noncash_value_per_old_share
    )


def continuing_event_gross_return(
    *,
    previous_raw_close: Decimal,
    ex_close: Decimal,
    share_multiplier: Decimal = ONE,
    cash_per_old_share: Decimal = ZERO,
    noncash_value_per_old_share: Decimal = ZERO,
) -> Decimal:
    if previous_raw_close <= ZERO:
        raise DataContractError("previous_raw_close must be positive")
    return continuing_event_value(
        ex_close=ex_close,
        share_multiplier=share_multiplier,
        cash_per_old_share=cash_per_old_share,
        noncash_value_per_old_share=noncash_value_per_old_share,
    ) / previous_raw_close


def continuing_event_backward_factor(
    *,
    ex_close: Decimal,
    share_multiplier: Decimal = ONE,
    cash_per_old_share: Decimal = ZERO,
    noncash_value_per_old_share: Decimal = ZERO,
) -> Decimal:
    return ex_close / continuing_event_value(
        ex_close=ex_close,
        share_multiplier=share_multiplier,
        cash_per_old_share=cash_per_old_share,
        noncash_value_per_old_share=noncash_value_per_old_share,
    )


@dataclass(frozen=True, slots=True)
class CorporateActionValuation:
    valuation_id: str
    action_id: str
    instrument_id: UUID
    purpose: ActionValuationPurpose
    valued_at: datetime
    available_at: datetime
    value_per_old_share: Decimal
    currency: str
    method: ActionValuationMethod
    source_snapshot_id: str
    revision: int = 0
    component_instrument_id: UUID | None = None
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.valuation_id.strip() or not self.action_id.strip():
            raise DataContractError("valuation_id and action_id are required")
        if not self.source_snapshot_id.strip() or not self.currency.strip():
            raise DataContractError("valuation source and currency are required")
        valued = require_aware(self.valued_at, "valued_at")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "valued_at", valued)
        object.__setattr__(self, "available_at", available)
        if available < valued:
            raise DataContractError("valuation available_at cannot precede valued_at")
        if self.value_per_old_share < ZERO:
            raise DataContractError("value_per_old_share cannot be negative")
        if self.revision < 0:
            raise DataContractError("valuation revision cannot be negative")


@dataclass(frozen=True, slots=True)
class CorporateActionCoverage:
    instrument_id: UUID
    covered_through: datetime
    available_at: datetime
    covered_types: frozenset[CorporateActionType]
    source_snapshot_id: str
    complete: bool
    revision: int = 0

    def __post_init__(self) -> None:
        covered = require_aware(self.covered_through, "covered_through")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "covered_through", covered)
        object.__setattr__(self, "available_at", available)
        object.__setattr__(self, "covered_types", frozenset(self.covered_types))
        if not self.source_snapshot_id.strip():
            raise DataContractError("coverage source_snapshot_id is required")
        if self.revision < 0:
            raise DataContractError("coverage revision cannot be negative")


@dataclass(frozen=True, slots=True)
class ActionEventFactor:
    instrument_id: UUID
    session_date: date
    effective_at: datetime
    available_at: datetime
    action_ids: tuple[str, ...]
    share_multiplier: Decimal
    cash_per_old_share: Decimal
    noncash_value_per_old_share: Decimal
    backward_split_factor: Decimal | None
    backward_total_return_factor: Decimal | None
    terminal: bool
    terminal_value_per_old_share: Decimal | None
    source_snapshot_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdjustedPriceObservation:
    instrument_id: UUID
    session_date: date
    observed_at: datetime
    available_at: datetime
    raw_close: Decimal
    split_adjusted_close: Decimal
    total_return_adjusted_close: Decimal
    cumulative_split_factor: Decimal
    cumulative_total_return_factor: Decimal
    applied_future_action_ids: tuple[str, ...]
    source_snapshot_ids: tuple[str, ...]
    adjustment_version: str


@dataclass(frozen=True, slots=True)
class TotalReturnObservation:
    instrument_id: UUID
    session_date: date
    observed_at: datetime
    available_at: datetime
    raw_close: Decimal | None
    gross_return: Decimal
    net_return: Decimal
    total_return_index: Decimal
    cash_distribution_per_old_share: Decimal
    noncash_distribution_value_per_old_share: Decimal
    share_multiplier: Decimal
    action_ids: tuple[str, ...]
    terminal: bool
    source_snapshot_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TotalReturnBuild:
    instrument_id: UUID
    decision_at: datetime
    reporting_currency: str
    adjusted_prices: tuple[AdjustedPriceObservation, ...]
    total_returns: tuple[TotalReturnObservation, ...]
    event_factors: tuple[ActionEventFactor, ...]
    input_snapshot_ids: tuple[str, ...]
    build_hash: str


@dataclass(frozen=True, slots=True)
class DistributedPosition:
    instrument_id: UUID
    quantity: Decimal
    action_id: str


@dataclass(frozen=True, slots=True)
class PositionActionEffect:
    instrument_id: UUID
    effective_at: datetime
    original_quantity: Decimal
    resulting_parent_quantity: Decimal
    cash_flow: Decimal
    fair_value_of_noncash_distributions: Decimal
    distributed_positions: tuple[DistributedPosition, ...]
    terminal: bool
    action_ids: tuple[str, ...]
    available_at: datetime
    effect_hash: str


def _record_revision(record: object) -> int:
    if hasattr(record, "revision"):
        return int(getattr(record, "revision"))
    if hasattr(record, "provider_revision"):
        return int(getattr(record, "provider_revision"))
    return 0


def _latest_known_by_key(
    records: Iterable[object],
    *,
    decision_at: datetime,
    key_fn,
) -> dict[object, object]:
    decision = require_aware(decision_at, "decision_at")
    grouped: dict[object, list[object]] = {}
    for record in records:
        available = require_aware(getattr(record, "available_at"), "record.available_at")
        if available <= decision:
            grouped.setdefault(key_fn(record), []).append(record)
    selected: dict[object, object] = {}
    for key, candidates in grouped.items():
        latest_key = max(
            (require_aware(getattr(item, "available_at"), "record.available_at"), _record_revision(item))
            for item in candidates
        )
        latest = [
            item
            for item in candidates
            if (
                require_aware(getattr(item, "available_at"), "record.available_at"),
                _record_revision(item),
            )
            == latest_key
        ]
        if len({repr(item) for item in latest}) > 1:
            raise PointInTimeError(
                f"conflicting point-in-time records for {key!r} share latest availability and revision"
            )
        selected[key] = latest[0]
    return selected


def select_actions_as_of(
    actions: Iterable[CorporateAction],
    *,
    instrument_id: UUID,
    decision_at: datetime,
) -> tuple[CorporateAction, ...]:
    relevant = tuple(action for action in actions if action.instrument_id == instrument_id)
    identity_by_id: dict[str, tuple[UUID, CorporateActionType]] = {}
    for action in relevant:
        identity = (action.instrument_id, action.action_type)
        prior = identity_by_id.setdefault(action.action_id, identity)
        if prior != identity:
            raise DataContractError(
                f"corporate-action identity changed across revisions: {action.action_id}"
            )
    selected = _latest_known_by_key(
        relevant, decision_at=decision_at, key_fn=lambda item: item.action_id
    )
    active = [
        action
        for action in selected.values()
        if action.status != CorporateActionStatus.CANCELLED
    ]
    return tuple(
        sorted(
            active,
            key=lambda item: (
                item.effective_at,
                item.available_at,
                item.action_type.value,
                item.action_id,
            ),
        )
    )


def select_valuations_as_of(
    valuations: Iterable[CorporateActionValuation],
    *,
    instrument_id: UUID,
    decision_at: datetime,
) -> tuple[CorporateActionValuation, ...]:
    relevant = tuple(item for item in valuations if item.instrument_id == instrument_id)
    selected = _latest_known_by_key(
        relevant,
        decision_at=decision_at,
        key_fn=lambda item: (item.action_id, item.purpose),
    )
    return tuple(
        sorted(
            selected.values(),
            key=lambda item: (item.valued_at, item.action_id, item.purpose.value),
        )
    )


def select_bars_as_of(
    bars: Iterable[DailyBar],
    *,
    instrument_id: UUID,
    decision_at: datetime,
) -> tuple[DailyBar, ...]:
    relevant = tuple(bar for bar in bars if bar.instrument_id == instrument_id)
    selected = _latest_known_by_key(
        relevant,
        decision_at=decision_at,
        key_fn=lambda item: item.session_date,
    )
    result = tuple(sorted(selected.values(), key=lambda item: item.session_date))
    if len(result) < 2:
        raise PointInTimeError("at least two point-in-time daily bars are required")
    if any(bar.quality_status != DataQualityStatus.VALID for bar in result):
        raise DataContractError("total-return build requires VALID daily bars")
    return result


def select_coverage_as_of(
    coverage: Iterable[CorporateActionCoverage],
    *,
    instrument_id: UUID,
    decision_at: datetime,
) -> CorporateActionCoverage:
    relevant = tuple(item for item in coverage if item.instrument_id == instrument_id)
    selected = _latest_known_by_key(
        relevant, decision_at=decision_at, key_fn=lambda item: item.instrument_id
    )
    if instrument_id not in selected:
        raise PointInTimeError("no corporate-action coverage record was available")
    return selected[instrument_id]  # type: ignore[return-value]


def _event_date(instant: datetime, exchange_timezone: ZoneInfo) -> date:
    return require_aware(instant, "effective_at").astimezone(exchange_timezone).date()


def _valuation_for(
    action: CorporateAction,
    purpose: ActionValuationPurpose,
    valuations_by_key: Mapping[tuple[str, ActionValuationPurpose], CorporateActionValuation],
    *,
    reporting_currency: str,
) -> CorporateActionValuation:
    key = (action.action_id, purpose)
    if key not in valuations_by_key:
        raise PointInTimeError(
            f"corporate action {action.action_id} lacks {purpose.value} valuation"
        )
    valuation = valuations_by_key[key]
    if valuation.currency.upper() != reporting_currency.upper():
        raise DataContractError(
            f"valuation currency mismatch for {action.action_id}: {valuation.currency}"
        )
    if valuation.valued_at < action.effective_at:
        raise DataContractError(
            f"valuation for {action.action_id} precedes the action effective time"
        )
    return valuation


def _cash_amount(action: CorporateAction, reporting_currency: str) -> Decimal:
    if action.cash_amount is None:
        return ZERO
    if not action.currency or action.currency.upper() != reporting_currency.upper():
        raise DataContractError(
            f"cash-action currency mismatch for {action.action_id}: {action.currency!r}"
        )
    return action.cash_amount


def _validate_coverage(
    coverage: CorporateActionCoverage,
    *,
    through: datetime,
    required_types: frozenset[CorporateActionType],
) -> None:
    if not coverage.complete:
        raise PointInTimeError("corporate-action coverage is not marked complete")
    if coverage.covered_through < require_aware(through, "coverage through"):
        raise PointInTimeError("corporate-action coverage does not reach the last required event time")
    missing = required_types.difference(coverage.covered_types)
    if missing:
        raise PointInTimeError(
            "corporate-action coverage lacks required types: "
            + ", ".join(sorted(item.value for item in missing))
        )


def _build_event_factors(
    *,
    instrument_id: UUID,
    bars: tuple[DailyBar, ...],
    actions: tuple[CorporateAction, ...],
    valuations: tuple[CorporateActionValuation, ...],
    decision_at: datetime,
    reporting_currency: str,
    exchange_timezone: ZoneInfo,
) -> tuple[ActionEventFactor, ...]:
    decision = require_aware(decision_at, "decision_at")
    bars_by_date = {bar.session_date: bar for bar in bars}
    valuation_map = {(item.action_id, item.purpose): item for item in valuations}
    grouped: dict[date, list[CorporateAction]] = {}
    first_bar_date = bars[0].session_date
    for action in actions:
        if action.effective_at > decision:
            continue
        event_date = _event_date(action.effective_at, exchange_timezone)
        # Actions before the selected price history are already embodied in the
        # first raw bar and must not require unavailable ex-date bars.
        if event_date < first_bar_date:
            continue
        grouped.setdefault(event_date, []).append(action)

    factors: list[ActionEventFactor] = []
    for session_date in sorted(grouped):
        day_actions = sorted(grouped[session_date], key=lambda item: (item.action_type.value, item.action_id))
        unsupported = [item for item in day_actions if item.action_type in UNSUPPORTED_MATERIAL_TYPES]
        if unsupported:
            raise PointInTimeError(
                "unsupported material corporate action(s): "
                + ", ".join(item.action_id for item in unsupported)
            )
        economic = [
            item
            for item in day_actions
            if item.action_type in CONTINUING_ECONOMIC_TYPES | TERMINAL_ECONOMIC_TYPES
        ]
        if not economic:
            continue
        if session_date == first_bar_date:
            raise PointInTimeError(
                "economic action occurs on the first selected bar; a prior bar is required"
            )
        continuing = [item for item in economic if item.action_type in CONTINUING_ECONOMIC_TYPES]
        terminal = [item for item in economic if item.action_type in TERMINAL_ECONOMIC_TYPES]
        if continuing and terminal:
            raise PointInTimeError(
                f"continuing and terminal actions share {session_date}; economic ordering is ambiguous"
            )
        if len(terminal) > 1:
            raise PointInTimeError(f"multiple terminal actions share {session_date}")

        source_ids = {item.source_snapshot_id for item in economic}
        availabilities = [item.available_at for item in economic]
        action_ids = tuple(item.action_id for item in economic)

        if terminal:
            action = terminal[0]
            cash = _cash_amount(action, reporting_currency)
            noncash = ZERO
            if action.stock_ratio is not None and action.stock_ratio > ZERO:
                valuation = _valuation_for(
                    action,
                    ActionValuationPurpose.TERMINAL_CONSIDERATION,
                    valuation_map,
                    reporting_currency=reporting_currency,
                )
                noncash = valuation.value_per_old_share
                source_ids.add(valuation.source_snapshot_id)
                availabilities.append(valuation.available_at)
            elif action.action_type in {
                CorporateActionType.BANKRUPTCY,
                CorporateActionType.DELISTING,
                CorporateActionType.LIQUIDATION,
            } and action.cash_amount is None:
                valuation = _valuation_for(
                    action,
                    ActionValuationPurpose.TERMINAL_CONSIDERATION,
                    valuation_map,
                    reporting_currency=reporting_currency,
                )
                noncash = valuation.value_per_old_share
                source_ids.add(valuation.source_snapshot_id)
                availabilities.append(valuation.available_at)
            terminal_value = cash + noncash
            factors.append(
                ActionEventFactor(
                    instrument_id=instrument_id,
                    session_date=session_date,
                    effective_at=action.effective_at,
                    available_at=max(availabilities),
                    action_ids=action_ids,
                    share_multiplier=ZERO,
                    cash_per_old_share=cash,
                    noncash_value_per_old_share=noncash,
                    backward_split_factor=None,
                    backward_total_return_factor=None,
                    terminal=True,
                    terminal_value_per_old_share=terminal_value,
                    source_snapshot_ids=tuple(sorted(source_ids)),
                )
            )
            continue

        if session_date not in bars_by_date:
            raise PointInTimeError(
                f"continuing corporate action on {session_date} lacks an ex-date daily bar"
            )
        ex_close = bars_by_date[session_date].close
        share_multiplier = ONE
        cash = ZERO
        noncash = ZERO
        for action in continuing:
            if action.action_type in {CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT}:
                assert action.split_new_shares is not None
                assert action.split_old_shares is not None
                share_multiplier *= action.split_new_shares / action.split_old_shares
            elif action.action_type == CorporateActionType.STOCK_DIVIDEND:
                assert action.stock_ratio is not None
                share_multiplier *= ONE + action.stock_ratio
            elif action.action_type == CorporateActionType.CASH_DIVIDEND:
                cash += _cash_amount(action, reporting_currency)
            elif action.action_type == CorporateActionType.SPINOFF:
                valuation = _valuation_for(
                    action,
                    ActionValuationPurpose.DISTRIBUTION,
                    valuation_map,
                    reporting_currency=reporting_currency,
                )
                noncash += valuation.value_per_old_share
                source_ids.add(valuation.source_snapshot_id)
                availabilities.append(valuation.available_at)
        economic_end_value = continuing_event_value(
            ex_close=ex_close,
            share_multiplier=share_multiplier,
            cash_per_old_share=cash,
            noncash_value_per_old_share=noncash,
        )
        factors.append(
            ActionEventFactor(
                instrument_id=instrument_id,
                session_date=session_date,
                effective_at=min(item.effective_at for item in continuing),
                available_at=max(availabilities),
                action_ids=action_ids,
                share_multiplier=share_multiplier,
                cash_per_old_share=cash,
                noncash_value_per_old_share=noncash,
                backward_split_factor=ONE / share_multiplier,
                backward_total_return_factor=continuing_event_backward_factor(
                    ex_close=ex_close,
                    share_multiplier=share_multiplier,
                    cash_per_old_share=cash,
                    noncash_value_per_old_share=noncash,
                ),
                terminal=False,
                terminal_value_per_old_share=None,
                source_snapshot_ids=tuple(sorted(source_ids)),
            )
        )
    return tuple(factors)


def build_total_return_as_of(
    *,
    instrument_id: UUID,
    bars: Iterable[DailyBar],
    actions: Iterable[CorporateAction],
    valuations: Iterable[CorporateActionValuation],
    coverage: Iterable[CorporateActionCoverage],
    decision_at: datetime,
    reporting_currency: str = "USD",
    exchange_timezone: str = "America/New_York",
    base_index: Decimal = Decimal("100"),
    required_coverage_types: frozenset[CorporateActionType] = DEFAULT_REQUIRED_COVERAGE_TYPES,
) -> TotalReturnBuild:
    """Build split and total-return price series using only information known as of decision_at."""
    decision = require_aware(decision_at, "decision_at")
    if base_index <= ZERO:
        raise DataContractError("base_index must be positive")
    if not reporting_currency.strip():
        raise DataContractError("reporting_currency is required")
    timezone = ZoneInfo(exchange_timezone)
    selected_bars = select_bars_as_of(bars, instrument_id=instrument_id, decision_at=decision)
    selected_actions = select_actions_as_of(actions, instrument_id=instrument_id, decision_at=decision)
    selected_valuations = select_valuations_as_of(
        valuations, instrument_id=instrument_id, decision_at=decision
    )
    selected_coverage = select_coverage_as_of(
        coverage, instrument_id=instrument_id, decision_at=decision
    )
    latest_required_time = max(selected_bars[-1].observed_at, decision)
    _validate_coverage(
        selected_coverage,
        through=latest_required_time,
        required_types=required_coverage_types,
    )
    factors = _build_event_factors(
        instrument_id=instrument_id,
        bars=selected_bars,
        actions=selected_actions,
        valuations=selected_valuations,
        decision_at=decision,
        reporting_currency=reporting_currency,
        exchange_timezone=timezone,
    )
    continuing_by_date = {item.session_date: item for item in factors if not item.terminal}
    terminal = tuple(item for item in factors if item.terminal)
    if len(terminal) > 1:
        raise PointInTimeError("multiple terminal events are visible in one instrument build")
    if terminal and terminal[0].session_date <= selected_bars[-1].session_date:
        raise PointInTimeError(
            "terminal event must follow the final parent trading bar; same-day sequencing is ambiguous"
        )

    build_input = {
        "instrument_id": instrument_id,
        "decision_at": decision,
        "reporting_currency": reporting_currency.upper(),
        "bars": selected_bars,
        "actions": selected_actions,
        "valuations": selected_valuations,
        "coverage": selected_coverage,
        "factors": factors,
    }
    build_hash = content_hash(build_input)

    cumulative_split = ONE
    cumulative_total = ONE
    future_action_ids: list[str] = []
    future_sources: set[str] = set()
    future_available: list[datetime] = []
    adjusted_reversed: list[AdjustedPriceObservation] = []
    for bar in reversed(selected_bars):
        source_ids = {bar.snapshot_id, selected_coverage.source_snapshot_id} | future_sources
        available = max([bar.available_at, selected_coverage.available_at, *future_available])
        adjusted_reversed.append(
            AdjustedPriceObservation(
                instrument_id=instrument_id,
                session_date=bar.session_date,
                observed_at=bar.observed_at,
                available_at=available,
                raw_close=bar.close,
                split_adjusted_close=bar.close * cumulative_split,
                total_return_adjusted_close=bar.close * cumulative_total,
                cumulative_split_factor=cumulative_split,
                cumulative_total_return_factor=cumulative_total,
                applied_future_action_ids=tuple(sorted(future_action_ids)),
                source_snapshot_ids=tuple(sorted(source_ids)),
                adjustment_version=build_hash,
            )
        )
        factor = continuing_by_date.get(bar.session_date)
        if factor is not None:
            assert factor.backward_split_factor is not None
            assert factor.backward_total_return_factor is not None
            cumulative_split *= factor.backward_split_factor
            cumulative_total *= factor.backward_total_return_factor
            future_action_ids.extend(factor.action_ids)
            future_sources.update(factor.source_snapshot_ids)
            future_available.append(factor.available_at)
    adjusted_prices = tuple(reversed(adjusted_reversed))

    returns: list[TotalReturnObservation] = []
    first = selected_bars[0]
    running_index = base_index
    running_available = max(first.available_at, selected_coverage.available_at)
    running_sources = {first.snapshot_id, selected_coverage.source_snapshot_id}
    returns.append(
        TotalReturnObservation(
            instrument_id=instrument_id,
            session_date=first.session_date,
            observed_at=first.observed_at,
            available_at=running_available,
            raw_close=first.close,
            gross_return=ONE,
            net_return=ZERO,
            total_return_index=running_index,
            cash_distribution_per_old_share=ZERO,
            noncash_distribution_value_per_old_share=ZERO,
            share_multiplier=ONE,
            action_ids=(),
            terminal=False,
            source_snapshot_ids=tuple(sorted(running_sources)),
        )
    )
    previous = first
    for current in selected_bars[1:]:
        factor = continuing_by_date.get(current.session_date)
        share_multiplier = factor.share_multiplier if factor else ONE
        cash = factor.cash_per_old_share if factor else ZERO
        noncash = factor.noncash_value_per_old_share if factor else ZERO
        gross_return = continuing_event_gross_return(
            previous_raw_close=previous.close,
            ex_close=current.close,
            share_multiplier=share_multiplier,
            cash_per_old_share=cash,
            noncash_value_per_old_share=noncash,
        )
        running_index *= gross_return
        inputs_available = [running_available, current.available_at]
        current_sources = set(running_sources) | {current.snapshot_id}
        action_ids: tuple[str, ...] = ()
        if factor:
            inputs_available.append(factor.available_at)
            current_sources.update(factor.source_snapshot_ids)
            action_ids = factor.action_ids
        running_available = max(inputs_available)
        running_sources = current_sources
        returns.append(
            TotalReturnObservation(
                instrument_id=instrument_id,
                session_date=current.session_date,
                observed_at=current.observed_at,
                available_at=running_available,
                raw_close=current.close,
                gross_return=gross_return,
                net_return=gross_return - ONE,
                total_return_index=running_index,
                cash_distribution_per_old_share=cash,
                noncash_distribution_value_per_old_share=noncash,
                share_multiplier=share_multiplier,
                action_ids=action_ids,
                terminal=False,
                source_snapshot_ids=tuple(sorted(current_sources)),
            )
        )
        previous = current

    if terminal:
        event = terminal[0]
        assert event.terminal_value_per_old_share is not None
        gross_return = event.terminal_value_per_old_share / previous.close
        running_index *= gross_return
        terminal_sources = running_sources | set(event.source_snapshot_ids)
        running_available = max(running_available, event.available_at)
        returns.append(
            TotalReturnObservation(
                instrument_id=instrument_id,
                session_date=event.session_date,
                observed_at=event.effective_at,
                available_at=running_available,
                raw_close=None,
                gross_return=gross_return,
                net_return=gross_return - ONE,
                total_return_index=running_index,
                cash_distribution_per_old_share=event.cash_per_old_share,
                noncash_distribution_value_per_old_share=event.noncash_value_per_old_share,
                share_multiplier=ZERO,
                action_ids=event.action_ids,
                terminal=True,
                source_snapshot_ids=tuple(sorted(terminal_sources)),
            )
        )

    all_sources = {
        selected_coverage.source_snapshot_id,
        *(bar.snapshot_id for bar in selected_bars),
        *(action.source_snapshot_id for action in selected_actions),
        *(valuation.source_snapshot_id for valuation in selected_valuations),
    }
    return TotalReturnBuild(
        instrument_id=instrument_id,
        decision_at=decision,
        reporting_currency=reporting_currency.upper(),
        adjusted_prices=adjusted_prices,
        total_returns=tuple(returns),
        event_factors=factors,
        input_snapshot_ids=tuple(sorted(all_sources)),
        build_hash=build_hash,
    )


def apply_actions_to_position_as_of(
    *,
    instrument_id: UUID,
    quantity: Decimal,
    effective_at: datetime,
    actions: Iterable[CorporateAction],
    valuations: Iterable[CorporateActionValuation],
    decision_at: datetime,
    reporting_currency: str = "USD",
    exchange_timezone: str = "America/New_York",
) -> PositionActionEffect:
    """Apply a same-session action bundle to a signed position quantity.

    Positive quantities are long and negative quantities are short. Cash and
    distributed-security quantities therefore inherit the sign automatically;
    a short cash dividend becomes a negative cash flow.
    """
    effective = require_aware(effective_at, "effective_at")
    decision = require_aware(decision_at, "decision_at")
    timezone = ZoneInfo(exchange_timezone)
    target_date = _event_date(effective, timezone)
    selected_actions = tuple(
        action
        for action in select_actions_as_of(
            actions, instrument_id=instrument_id, decision_at=decision
        )
        if _event_date(action.effective_at, timezone) == target_date
    )
    selected_valuations = select_valuations_as_of(
        valuations, instrument_id=instrument_id, decision_at=decision
    )
    valuation_map = {(item.action_id, item.purpose): item for item in selected_valuations}
    economic = tuple(
        action
        for action in selected_actions
        if action.action_type in CONTINUING_ECONOMIC_TYPES | TERMINAL_ECONOMIC_TYPES
    )
    if not economic:
        raise PointInTimeError("no economic corporate action exists on the effective date")
    if any(action.action_type in UNSUPPORTED_MATERIAL_TYPES for action in selected_actions):
        raise PointInTimeError("unsupported material action cannot be applied to a position")
    terminal_actions = [item for item in economic if item.action_type in TERMINAL_ECONOMIC_TYPES]
    continuing_actions = [item for item in economic if item.action_type in CONTINUING_ECONOMIC_TYPES]
    if terminal_actions and continuing_actions:
        raise PointInTimeError("mixed continuing and terminal position effects are ambiguous")
    if len(terminal_actions) > 1:
        raise PointInTimeError("multiple terminal position effects are ambiguous")

    cash_flow = ZERO
    noncash_fair_value = ZERO
    resulting_quantity = quantity
    distributed: list[DistributedPosition] = []
    availability = [item.available_at for item in economic]

    if terminal_actions:
        action = terminal_actions[0]
        cash = _cash_amount(action, reporting_currency)
        cash_flow += quantity * cash
        if action.stock_ratio is not None and action.stock_ratio > ZERO:
            assert action.successor_instrument_id is not None
            distributed.append(
                DistributedPosition(
                    instrument_id=action.successor_instrument_id,
                    quantity=quantity * action.stock_ratio,
                    action_id=action.action_id,
                )
            )
            valuation = _valuation_for(
                action,
                ActionValuationPurpose.TERMINAL_CONSIDERATION,
                valuation_map,
                reporting_currency=reporting_currency,
            )
            noncash_fair_value += quantity * valuation.value_per_old_share
            availability.append(valuation.available_at)
        elif action.cash_amount is None:
            valuation = _valuation_for(
                action,
                ActionValuationPurpose.TERMINAL_CONSIDERATION,
                valuation_map,
                reporting_currency=reporting_currency,
            )
            noncash_fair_value += quantity * valuation.value_per_old_share
            availability.append(valuation.available_at)
        resulting_quantity = ZERO
    else:
        share_multiplier = ONE
        for action in continuing_actions:
            if action.action_type in {CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT}:
                assert action.split_new_shares is not None and action.split_old_shares is not None
                share_multiplier *= action.split_new_shares / action.split_old_shares
            elif action.action_type == CorporateActionType.STOCK_DIVIDEND:
                assert action.stock_ratio is not None
                share_multiplier *= ONE + action.stock_ratio
            elif action.action_type == CorporateActionType.CASH_DIVIDEND:
                cash_flow += quantity * _cash_amount(action, reporting_currency)
            elif action.action_type == CorporateActionType.SPINOFF:
                assert action.child_instrument_id is not None and action.stock_ratio is not None
                distributed.append(
                    DistributedPosition(
                        instrument_id=action.child_instrument_id,
                        quantity=quantity * action.stock_ratio,
                        action_id=action.action_id,
                    )
                )
                valuation = _valuation_for(
                    action,
                    ActionValuationPurpose.DISTRIBUTION,
                    valuation_map,
                    reporting_currency=reporting_currency,
                )
                noncash_fair_value += quantity * valuation.value_per_old_share
                availability.append(valuation.available_at)
        resulting_quantity = quantity * share_multiplier

    payload = {
        "instrument_id": instrument_id,
        "effective_at": effective,
        "quantity": quantity,
        "actions": economic,
        "valuations": selected_valuations,
        "cash_flow": cash_flow,
        "noncash_fair_value": noncash_fair_value,
        "resulting_quantity": resulting_quantity,
        "distributed": distributed,
    }
    return PositionActionEffect(
        instrument_id=instrument_id,
        effective_at=effective,
        original_quantity=quantity,
        resulting_parent_quantity=resulting_quantity,
        cash_flow=cash_flow,
        fair_value_of_noncash_distributions=noncash_fair_value,
        distributed_positions=tuple(distributed),
        terminal=bool(terminal_actions),
        action_ids=tuple(item.action_id for item in economic),
        available_at=max(availability),
        effect_hash=content_hash(payload),
    )

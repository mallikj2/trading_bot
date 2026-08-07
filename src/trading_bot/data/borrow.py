"""Historical short-borrow availability and borrow-cost contracts.

The module deliberately distinguishes historical research evidence from live
broker authorization.  A market-composite lending observation can support a
historical research simulation, but it can never authorize a live short order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import UUID

from .errors import DataContractError, PointInTimeError
from .time_utils import require_aware


class BorrowAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class BorrowDifficulty(str, Enum):
    EASY = "EASY"
    HARD = "HARD"
    UNKNOWN = "UNKNOWN"


class BorrowSourceKind(str, Enum):
    BROKER_SPECIFIC = "BROKER_SPECIFIC"
    MARKET_COMPOSITE = "MARKET_COMPOSITE"
    REGULATORY_PROXY = "REGULATORY_PROXY"


class BorrowEventType(str, Enum):
    RECALL = "RECALL"
    BUY_IN = "BUY_IN"
    AVAILABILITY_WITHDRAWN = "AVAILABILITY_WITHDRAWN"
    BROKER_RESTRICTION = "BROKER_RESTRICTION"


class BorrowEligibilityReason(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    MISSING_OBSERVATION = "MISSING_OBSERVATION"
    EXPIRED_OBSERVATION = "EXPIRED_OBSERVATION"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    MISSING_RATE = "MISSING_RATE"
    MISSING_QUANTITY = "MISSING_QUANTITY"
    INSUFFICIENT_QUANTITY = "INSUFFICIENT_QUANTITY"
    HARD_TO_BORROW_BLOCKED = "HARD_TO_BORROW_BLOCKED"
    SOURCE_NOT_APPROVED = "SOURCE_NOT_APPROVED"
    BROKER_SPECIFIC_REQUIRED = "BROKER_SPECIFIC_REQUIRED"
    RATE_ABOVE_POLICY = "RATE_ABOVE_POLICY"
    ACTIVE_RECALL_OR_RESTRICTION = "ACTIVE_RECALL_OR_RESTRICTION"


@dataclass(frozen=True, slots=True)
class BorrowObservation:
    instrument_id: UUID
    observed_at: datetime
    available_at: datetime
    expires_at: datetime
    availability: BorrowAvailability
    difficulty: BorrowDifficulty
    provider: str
    environment: str
    source_kind: BorrowSourceKind
    source_snapshot_id: str
    revision: int = 0
    annual_fee_rate: Decimal | None = None
    available_shares: int | None = None
    locate_or_confirmation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        observed = require_aware(self.observed_at, "observed_at")
        available = require_aware(self.available_at, "available_at")
        expires = require_aware(self.expires_at, "expires_at")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "available_at", available)
        object.__setattr__(self, "expires_at", expires)
        if available < observed:
            raise DataContractError("borrow available_at cannot precede observed_at")
        if expires <= available:
            raise DataContractError("borrow expires_at must be later than available_at")
        if self.annual_fee_rate is not None and self.annual_fee_rate < 0:
            raise DataContractError("borrow annual_fee_rate cannot be negative")
        if self.available_shares is not None and self.available_shares < 0:
            raise DataContractError("available_shares cannot be negative")
        if self.revision < 0:
            raise DataContractError("borrow revision cannot be negative")
        if not self.provider.strip() or not self.environment.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("borrow provider, environment and source_snapshot_id are required")
        if self.source_kind == BorrowSourceKind.REGULATORY_PROXY and self.availability == BorrowAvailability.AVAILABLE:
            raise DataContractError("regulatory proxy data cannot assert borrow availability")


@dataclass(frozen=True, slots=True)
class BorrowCoverageObservation:
    """Explicit dense/sparse coverage declaration for one instrument.

    Coverage is intentionally separate from a borrow observation.  Absence of a
    borrow row cannot be interpreted as unavailable unless the source contract
    explicitly states that the interval has complete dense coverage.
    """

    instrument_id: UUID
    covered_from: date
    covered_through: date
    available_at: datetime
    provider: str
    source_snapshot_id: str
    complete_daily_coverage: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "available_at", require_aware(self.available_at, "available_at"))
        if self.covered_through < self.covered_from:
            raise DataContractError("borrow coverage range is inverted")
        if not self.provider.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("borrow coverage provider and source_snapshot_id are required")


@dataclass(frozen=True, slots=True)
class BorrowEvent:
    instrument_id: UUID
    event_type: BorrowEventType
    effective_at: datetime
    available_at: datetime
    provider: str
    environment: str
    source_snapshot_id: str
    event_id: str
    revision: int = 0
    forced_exit: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        effective = require_aware(self.effective_at, "effective_at")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "effective_at", effective)
        object.__setattr__(self, "available_at", available)
        if self.revision < 0:
            raise DataContractError("borrow event revision cannot be negative")
        if not self.provider.strip() or not self.environment.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("borrow event provider, environment and source_snapshot_id are required")
        if not self.event_id.strip():
            raise DataContractError("borrow event_id is required")


@dataclass(frozen=True, slots=True)
class BorrowEligibilityDecision:
    allowed: bool
    reason: BorrowEligibilityReason
    observation: BorrowObservation | None = None
    blocking_event: BorrowEvent | None = None


@dataclass(frozen=True, slots=True)
class BorrowPolicy:
    """Explicit policy; no hidden economics are supplied by this module."""

    approved_provider: str
    require_broker_specific: bool
    allow_hard_to_borrow: bool
    require_available_shares: bool
    max_annual_fee_rate: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.approved_provider.strip():
            raise DataContractError("approved_provider is required")
        if self.max_annual_fee_rate is not None and self.max_annual_fee_rate < 0:
            raise DataContractError("max_annual_fee_rate cannot be negative")


def _same_context(rows: Sequence[BorrowObservation]) -> None:
    contexts = {(row.instrument_id, row.provider, row.environment) for row in rows}
    if len(contexts) > 1:
        raise DataContractError("borrow observations mix instruments/providers/environments")


def latest_borrow_observation_as_of(
    observations: Sequence[BorrowObservation],
    *,
    decision_at: datetime,
) -> BorrowObservation | None:
    """Return the latest unexpired revision known at ``decision_at``.

    Conflicting records at the same maximum (available_at, observed_at,
    revision) are rejected rather than tie-broken by snapshot id.
    """

    decision = require_aware(decision_at, "decision_at")
    if not observations:
        return None
    _same_context(observations)
    eligible = [row for row in observations if row.available_at <= decision and row.expires_at > decision]
    if not eligible:
        return None
    key = max((row.available_at, row.observed_at, row.revision) for row in eligible)
    winners = [row for row in eligible if (row.available_at, row.observed_at, row.revision) == key]
    if len(winners) != 1:
        raise PointInTimeError("ambiguous borrow observation at decision time")
    return winners[0]


def latest_borrow_event_as_of(
    events: Sequence[BorrowEvent],
    *,
    decision_at: datetime,
) -> BorrowEvent | None:
    decision = require_aware(decision_at, "decision_at")
    # A known future-effective recall/restriction is actionable as soon as the
    # notification is available.  Waiting until effective_at would permit a new
    # short after the broker/source has already announced the withdrawal.
    known = [event for event in events if event.available_at <= decision]
    if not known:
        return None
    contexts = {(event.instrument_id, event.provider, event.environment) for event in known}
    if len(contexts) > 1:
        raise DataContractError("borrow events mix instruments/providers/environments")
    key = max((event.available_at, event.effective_at, event.revision) for event in known)
    winners = [
        event
        for event in known
        if (event.available_at, event.effective_at, event.revision) == key
    ]
    if len(winners) != 1:
        raise PointInTimeError("ambiguous borrow event at decision time")
    return winners[0]


def evaluate_short_entry(
    observations: Sequence[BorrowObservation],
    *,
    decision_at: datetime,
    requested_shares: int,
    policy: BorrowPolicy,
    events: Sequence[BorrowEvent] = (),
) -> BorrowEligibilityDecision:
    """Fail-closed historical/live short-borrow gate."""

    if requested_shares <= 0:
        raise ValueError("requested_shares must be positive")
    decision = require_aware(decision_at, "decision_at")
    observation = latest_borrow_observation_as_of(observations, decision_at=decision)
    if observation is None:
        known = [row for row in observations if row.available_at <= decision]
        if known and all(row.expires_at <= decision for row in known):
            return BorrowEligibilityDecision(False, BorrowEligibilityReason.EXPIRED_OBSERVATION)
        return BorrowEligibilityDecision(False, BorrowEligibilityReason.MISSING_OBSERVATION)
    if observation.provider != policy.approved_provider:
        return BorrowEligibilityDecision(False, BorrowEligibilityReason.SOURCE_NOT_APPROVED, observation)
    if policy.require_broker_specific and observation.source_kind != BorrowSourceKind.BROKER_SPECIFIC:
        return BorrowEligibilityDecision(False, BorrowEligibilityReason.BROKER_SPECIFIC_REQUIRED, observation)

    matching_events = [
        event
        for event in events
        if event.instrument_id == observation.instrument_id
        and event.provider == observation.provider
        and event.environment == observation.environment
    ]
    event = latest_borrow_event_as_of(matching_events, decision_at=decision)
    if event is not None and event.forced_exit:
        return BorrowEligibilityDecision(
            False,
            BorrowEligibilityReason.ACTIVE_RECALL_OR_RESTRICTION,
            observation,
            event,
        )
    if observation.availability == BorrowAvailability.UNKNOWN:
        return BorrowEligibilityDecision(False, BorrowEligibilityReason.UNKNOWN, observation)
    if observation.availability == BorrowAvailability.UNAVAILABLE:
        return BorrowEligibilityDecision(False, BorrowEligibilityReason.UNAVAILABLE, observation)
    if observation.annual_fee_rate is None:
        return BorrowEligibilityDecision(False, BorrowEligibilityReason.MISSING_RATE, observation)
    if observation.difficulty == BorrowDifficulty.HARD and not policy.allow_hard_to_borrow:
        return BorrowEligibilityDecision(False, BorrowEligibilityReason.HARD_TO_BORROW_BLOCKED, observation)
    if policy.max_annual_fee_rate is not None and observation.annual_fee_rate > policy.max_annual_fee_rate:
        return BorrowEligibilityDecision(False, BorrowEligibilityReason.RATE_ABOVE_POLICY, observation)
    if policy.require_available_shares:
        if observation.available_shares is None:
            return BorrowEligibilityDecision(False, BorrowEligibilityReason.MISSING_QUANTITY, observation)
        if observation.available_shares < requested_shares:
            return BorrowEligibilityDecision(False, BorrowEligibilityReason.INSUFFICIENT_QUANTITY, observation)
    return BorrowEligibilityDecision(True, BorrowEligibilityReason.ELIGIBLE, observation)


@dataclass(frozen=True, slots=True)
class BorrowAccrualInput:
    session_date: date
    end_of_day_short_market_value: Decimal
    annual_fee_rate: Decimal
    calendar_days: int
    source_snapshot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.end_of_day_short_market_value < 0:
            raise DataContractError("short market value must be non-negative")
        if self.annual_fee_rate < 0:
            raise DataContractError("borrow annual fee rate must be non-negative")
        if self.calendar_days < 1:
            raise DataContractError("borrow accrual calendar_days must be at least one")
        if not self.source_snapshot_ids:
            raise DataContractError("borrow accrual requires source lineage")


@dataclass(frozen=True, slots=True)
class BorrowFeeAccrual:
    base_fee_usd: Decimal
    stressed_fee_usd: Decimal
    stress_multiplier: Decimal
    total_calendar_days: int
    lineage_snapshot_ids: tuple[str, ...]


def accrue_borrow_fees(
    rows: Sequence[BorrowAccrualInput],
    *,
    stress_multiplier: Decimal = Decimal("1"),
) -> BorrowFeeAccrual:
    """Accrue Schwab-style borrow fees from explicit daily inputs.

    Formula per explicit accrual interval:
        EOD short market value * annual quoted rate / 360 * calendar days

    The caller must determine settlement/accrual-start semantics.  This module
    intentionally does not invent a broker rule when the historical broker
    contract has not been validated.
    """

    if stress_multiplier < 1:
        raise DataContractError("stress_multiplier must be at least one")
    total = Decimal("0")
    days = 0
    lineage: set[str] = set()
    for row in rows:
        total += (
            row.end_of_day_short_market_value
            * row.annual_fee_rate
            / Decimal("360")
            * Decimal(row.calendar_days)
        )
        days += row.calendar_days
        lineage.update(row.source_snapshot_ids)
    return BorrowFeeAccrual(
        base_fee_usd=total,
        stressed_fee_usd=total * stress_multiplier,
        stress_multiplier=stress_multiplier,
        total_calendar_days=days,
        lineage_snapshot_ids=tuple(sorted(lineage)),
    )


def borrow_cost_bps(*, fee_usd: Decimal, entry_notional_usd: Decimal) -> Decimal:
    if fee_usd < 0:
        raise DataContractError("fee_usd cannot be negative")
    if entry_notional_usd <= 0:
        raise DataContractError("entry_notional_usd must be positive")
    return fee_usd / entry_notional_usd * Decimal("10000")


def validate_borrow_coverage(
    coverage: Sequence[BorrowCoverageObservation],
    *,
    instrument_id: UUID,
    session_date: date,
    decision_at: datetime,
    provider: str,
) -> bool:
    """Return True only when dense daily source coverage is explicitly known."""

    decision = require_aware(decision_at, "decision_at")
    rows = [
        row
        for row in coverage
        if row.instrument_id == instrument_id
        and row.provider == provider
        and row.available_at <= decision
        and row.covered_from <= session_date <= row.covered_through
    ]
    if not rows:
        return False
    if any(not row.complete_daily_coverage for row in rows):
        return False
    return True


@dataclass(frozen=True, slots=True)
class BorrowContinuationDecision:
    continue_position: bool
    exit_required: bool
    reason: BorrowEligibilityReason
    observation: BorrowObservation | None = None
    blocking_event: BorrowEvent | None = None


def evaluate_existing_short(
    observations: Sequence[BorrowObservation],
    *,
    decision_at: datetime,
    current_shares: int,
    policy: BorrowPolicy,
    events: Sequence[BorrowEvent] = (),
) -> BorrowContinuationDecision:
    """Daily fail-closed borrow validation for an already-open short position."""

    entry_like = evaluate_short_entry(
        observations,
        decision_at=decision_at,
        requested_shares=current_shares,
        policy=policy,
        events=events,
    )
    return BorrowContinuationDecision(
        continue_position=entry_like.allowed,
        exit_required=not entry_like.allowed,
        reason=entry_like.reason,
        observation=entry_like.observation,
        blocking_event=entry_like.blocking_event,
    )


def derive_availability_withdrawal_events(
    observations: Sequence[BorrowObservation],
) -> tuple[BorrowEvent, ...]:
    """Derive conservative withdrawal events from explicit state transitions.

    This is not represented as a broker recall.  It only means the approved
    historical source changed from AVAILABLE to UNAVAILABLE; the research
    engine therefore exits at the next permitted execution window.
    """

    if not observations:
        return ()
    _same_context(observations)
    rows = sorted(observations, key=lambda row: (row.observed_at, row.available_at, row.revision))
    events: list[BorrowEvent] = []
    previous: BorrowObservation | None = None
    for row in rows:
        if (
            previous is not None
            and previous.availability == BorrowAvailability.AVAILABLE
            and row.availability == BorrowAvailability.UNAVAILABLE
        ):
            events.append(
                BorrowEvent(
                    instrument_id=row.instrument_id,
                    event_type=BorrowEventType.AVAILABILITY_WITHDRAWN,
                    effective_at=row.observed_at,
                    available_at=row.available_at,
                    provider=row.provider,
                    environment=row.environment,
                    source_snapshot_id=row.source_snapshot_id,
                    event_id=f"availability-withdrawn:{row.source_snapshot_id}:{row.revision}",
                    revision=row.revision,
                    forced_exit=True,
                    metadata={"derived_from_state_transition": True},
                )
            )
        previous = row
    return tuple(events)

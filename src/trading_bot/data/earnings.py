"""Revision-aware earnings schedules for point-in-time strategy decisions.

This module deliberately separates *what the provider currently says* from
*what the strategy was allowed to know at a historical decision timestamp*.
Current calendars are never backfilled into earlier decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Iterable
from uuid import UUID

from .calendars import ExchangeCalendar
from .contracts import EarningsTiming
from .errors import CalendarError, DataContractError, PointInTimeError
from .pit import select_latest_known
from .time_utils import require_aware


class EarningsScheduleStatus(str, Enum):
    FORECAST = "FORECAST"
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    WITHDRAWN = "WITHDRAWN"
    COMPLETED = "COMPLETED"


class EarningsRevisionKind(str, Enum):
    INITIAL = "INITIAL"
    DATE_CHANGE = "DATE_CHANGE"
    TIME_CHANGE = "TIME_CHANGE"
    DATE_AND_TIME_CHANGE = "DATE_AND_TIME_CHANGE"
    STATUS_CHANGE = "STATUS_CHANGE"
    WITHDRAWAL = "WITHDRAWAL"
    RESTORE = "RESTORE"
    CORRECTION = "CORRECTION"


class EarningsEntryReason(str, Enum):
    CLEAR = "CLEAR"
    EARNINGS_WITHIN_MINIMUM_HOLD = "EARNINGS_WITHIN_MINIMUM_HOLD"
    INSUFFICIENT_FORWARD_COVERAGE = "INSUFFICIENT_FORWARD_COVERAGE"
    UNRESOLVED_EARNINGS_SCHEDULE = "UNRESOLVED_EARNINGS_SCHEDULE"
    REENTRY_BEFORE_POST_EVENT_CLOSE = "REENTRY_BEFORE_POST_EVENT_CLOSE"


class EarningsExitReason(str, Enum):
    NOT_DUE = "NOT_DUE"
    SCHEDULED_EARNINGS = "SCHEDULED_EARNINGS"
    LATE_SCHEDULE_REVISION = "LATE_SCHEDULE_REVISION"
    UNRESOLVED_SCHEDULE = "UNRESOLVED_SCHEDULE"


@dataclass(frozen=True, slots=True)
class EarningsScheduleRevision:
    """One immutable version of one fiscal-period earnings schedule."""

    instrument_id: UUID
    event_key: str
    fiscal_year: int
    fiscal_period: str
    scheduled_session: date | None
    timing: EarningsTiming
    status: EarningsScheduleStatus
    revision_kind: EarningsRevisionKind
    available_at: datetime
    ingested_at: datetime
    revision: int
    source_snapshot_id: str
    provider: str
    source_event_id: str | None = None
    source_url: str | None = None
    confidence: str | None = None

    def __post_init__(self) -> None:
        if not self.event_key.strip():
            raise DataContractError("event_key is required")
        if self.fiscal_year < 1900 or self.fiscal_year > 2200:
            raise DataContractError("fiscal_year is outside the supported range")
        if not self.fiscal_period.strip():
            raise DataContractError("fiscal_period is required")
        if self.revision < 0:
            raise DataContractError("revision cannot be negative")
        if not self.source_snapshot_id.strip() or not self.provider.strip():
            raise DataContractError("source_snapshot_id and provider are required")

        available = require_aware(self.available_at, "available_at")
        ingested = require_aware(self.ingested_at, "ingested_at")
        object.__setattr__(self, "available_at", available)
        object.__setattr__(self, "ingested_at", ingested)
        if ingested < available:
            raise DataContractError("ingested_at cannot precede available_at")

        active_statuses = {
            EarningsScheduleStatus.FORECAST,
            EarningsScheduleStatus.TENTATIVE,
            EarningsScheduleStatus.CONFIRMED,
            EarningsScheduleStatus.COMPLETED,
        }
        if self.status in active_statuses and self.scheduled_session is None:
            raise DataContractError("active/completed earnings records require scheduled_session")
        if self.status == EarningsScheduleStatus.WITHDRAWN:
            if self.revision_kind not in {
                EarningsRevisionKind.WITHDRAWAL,
                EarningsRevisionKind.CORRECTION,
            }:
                raise DataContractError("withdrawn schedule requires WITHDRAWAL/CORRECTION revision kind")


@dataclass(frozen=True, slots=True)
class EarningsCoverageObservation:
    """Proves that the provider calendar was complete through a forward date.

    This avoids confusing "no event record" with "missing provider data".
    """

    instrument_id: UUID
    covered_through: date
    available_at: datetime
    ingested_at: datetime
    revision: int
    source_snapshot_id: str
    provider: str
    complete: bool = True

    def __post_init__(self) -> None:
        if self.revision < 0:
            raise DataContractError("coverage revision cannot be negative")
        if not self.source_snapshot_id.strip() or not self.provider.strip():
            raise DataContractError("coverage source_snapshot_id and provider are required")
        available = require_aware(self.available_at, "coverage.available_at")
        ingested = require_aware(self.ingested_at, "coverage.ingested_at")
        object.__setattr__(self, "available_at", available)
        object.__setattr__(self, "ingested_at", ingested)
        if ingested < available:
            raise DataContractError("coverage ingested_at cannot precede available_at")


@dataclass(frozen=True, slots=True)
class EarningsEntryDecision:
    allowed: bool
    reason: EarningsEntryReason
    fill_session: date
    minimum_hold_end_session: date
    conflicting_event_key: str | None = None
    conflicting_event_session: date | None = None


@dataclass(frozen=True, slots=True)
class EarningsExitPlan:
    reason: EarningsExitReason
    required_exit_session: date | None
    execution_session: date | None
    late_revision: bool
    operational_exception: bool
    event_key: str



def validate_revision_sequence(revisions: Iterable[EarningsScheduleRevision]) -> tuple[EarningsScheduleRevision, ...]:
    """Validate an event's immutable schedule history and return it ordered.

    Revision numbers must increase as provider-availability timestamps increase.
    Equal timestamp/revision keys are prohibited even when payloads happen to be
    identical because that would make provider lineage ambiguous.
    """

    ordered = tuple(sorted(revisions, key=lambda r: (r.available_at, r.revision)))
    if not ordered:
        raise DataContractError("earnings revision sequence cannot be empty")

    first = ordered[0]
    identity = (first.instrument_id, first.event_key, first.fiscal_year, first.fiscal_period)
    seen_keys: set[tuple[datetime, int]] = set()
    prior_revision = -1
    prior_available: datetime | None = None

    for row in ordered:
        if (row.instrument_id, row.event_key, row.fiscal_year, row.fiscal_period) != identity:
            raise DataContractError("revision sequence mixes earnings events")
        key = (row.available_at, row.revision)
        if key in seen_keys:
            raise DataContractError("duplicate earnings availability/revision key")
        seen_keys.add(key)
        if row.revision <= prior_revision:
            raise DataContractError("earnings revisions must strictly increase")
        if prior_available is not None and row.available_at < prior_available:
            raise DataContractError("earnings availability must be monotonic")
        prior_revision = row.revision
        prior_available = row.available_at

    return ordered


def latest_schedule_as_of(
    revisions: Iterable[EarningsScheduleRevision],
    *,
    event_key: str,
    decision_at: datetime,
) -> EarningsScheduleRevision:
    """Return the latest schedule version that was known by ``decision_at``."""

    event_rows = [row for row in revisions if row.event_key == event_key]
    if not event_rows:
        raise PointInTimeError("no earnings schedule history exists for event_key")
    validate_revision_sequence(event_rows)
    return select_latest_known(
        event_rows,
        decision_at=decision_at,
    )


def latest_schedules_as_of(
    revisions: Iterable[EarningsScheduleRevision],
    *,
    instrument_id: UUID,
    decision_at: datetime,
) -> tuple[EarningsScheduleRevision, ...]:
    """Return one as-of version for every earnings event known for an instrument."""

    decision = require_aware(decision_at, "decision_at")
    rows = [r for r in revisions if r.instrument_id == instrument_id]
    by_key: dict[str, list[EarningsScheduleRevision]] = {}
    for row in rows:
        by_key.setdefault(row.event_key, []).append(row)

    selected: list[EarningsScheduleRevision] = []
    for event_key, event_rows in by_key.items():
        try:
            selected.append(latest_schedule_as_of(event_rows, event_key=event_key, decision_at=decision))
        except PointInTimeError:
            # The event existed in the imported history, but no version was yet known.
            continue

    return tuple(
        sorted(
            selected,
            key=lambda row: (
                row.scheduled_session or date.max,
                row.fiscal_year,
                row.fiscal_period,
                row.event_key,
            ),
        )
    )


def validate_coverage_sequence(
    observations: Iterable[EarningsCoverageObservation],
) -> tuple[EarningsCoverageObservation, ...]:
    ordered = tuple(sorted(observations, key=lambda r: (r.available_at, r.revision)))
    if not ordered:
        raise DataContractError("earnings coverage sequence cannot be empty")
    instrument_id = ordered[0].instrument_id
    providers = {row.provider for row in ordered}
    if len(providers) != 1:
        raise DataContractError("earnings coverage sequence cannot mix providers")
    seen: set[tuple[datetime, int]] = set()
    prior_revision = -1
    for row in ordered:
        if row.instrument_id != instrument_id:
            raise DataContractError("earnings coverage sequence mixes instruments")
        key = (row.available_at, row.revision)
        if key in seen:
            raise DataContractError("duplicate earnings coverage availability/revision key")
        seen.add(key)
        if row.revision <= prior_revision:
            raise DataContractError("earnings coverage revisions must strictly increase")
        prior_revision = row.revision
    return ordered


def latest_coverage_as_of(
    observations: Iterable[EarningsCoverageObservation],
    *,
    instrument_id: UUID,
    decision_at: datetime,
) -> EarningsCoverageObservation:
    rows = [row for row in observations if row.instrument_id == instrument_id]
    if not rows:
        raise PointInTimeError("no earnings coverage record was available")
    validate_coverage_sequence(rows)
    return select_latest_known(rows, decision_at=decision_at)


def _nth_session_from(calendar: ExchangeCalendar, start_session: date, count: int) -> date:
    if count <= 0:
        raise DataContractError("session count must be positive")
    current = calendar.session(start_session).session_date
    for _ in range(count - 1):
        current = calendar.next_session(current).session_date
    return current


def _post_event_decision_at(calendar: ExchangeCalendar, scheduled_session: date) -> datetime:
    """Conservative re-entry boundary for session or non-session event dates."""

    try:
        session = calendar.session(scheduled_session)
    except CalendarError:
        # For weekend/holiday events, require the first subsequent trading
        # session to close and validate before re-entry.
        prior = calendar.previous_session(scheduled_session)
        session = calendar.next_session(prior.session_date)
    return calendar.decision_at(session.session_date)


def required_earnings_exit_session(
    calendar: ExchangeCalendar,
    revision: EarningsScheduleRevision,
) -> date:
    """Map Phase 01 BMO/AMC/during/unknown rules to an exit session."""

    if revision.status == EarningsScheduleStatus.WITHDRAWN or revision.scheduled_session is None:
        raise DataContractError("withdrawn/unresolved earnings schedule has no planned exit session")

    event_date = revision.scheduled_session
    if revision.timing in {
        EarningsTiming.BMO,
        EarningsTiming.DURING_SESSION,
        EarningsTiming.UNKNOWN,
    }:
        return calendar.previous_session(event_date).session_date

    if revision.timing == EarningsTiming.AMC:
        # AMC is defined relative to a regular trading session. A provider
        # assigning AMC to a weekend/holiday is internally inconsistent.
        return calendar.session(event_date).session_date

    raise DataContractError(f"unsupported earnings timing: {revision.timing}")


def evaluate_new_entry(
    *,
    instrument_id: UUID,
    decision_session: date,
    decision_at: datetime,
    calendar: ExchangeCalendar,
    revisions: Iterable[EarningsScheduleRevision],
    coverage_observations: Iterable[EarningsCoverageObservation],
    minimum_holding_sessions: int = 10,
) -> EarningsEntryDecision:
    """Apply the Phase 01 no-entry-through-earnings rule point-in-time."""

    decision = require_aware(decision_at, "decision_at")
    if decision < calendar.decision_at(decision_session):
        raise DataContractError("earnings entry evaluation cannot precede the session decision timestamp")

    fill_session = calendar.next_session(decision_session).session_date
    hold_end = _nth_session_from(calendar, fill_session, minimum_holding_sessions)

    try:
        coverage = latest_coverage_as_of(
            coverage_observations,
            instrument_id=instrument_id,
            decision_at=decision,
        )
    except PointInTimeError:
        return EarningsEntryDecision(
            False,
            EarningsEntryReason.INSUFFICIENT_FORWARD_COVERAGE,
            fill_session,
            hold_end,
        )

    if not coverage.complete or coverage.covered_through < hold_end:
        return EarningsEntryDecision(
            False,
            EarningsEntryReason.INSUFFICIENT_FORWARD_COVERAGE,
            fill_session,
            hold_end,
        )

    schedules = latest_schedules_as_of(
        revisions,
        instrument_id=instrument_id,
        decision_at=decision,
    )

    for schedule in schedules:
        if schedule.status == EarningsScheduleStatus.WITHDRAWN:
            # A removed date is not evidence that the fiscal-period earnings
            # event disappeared. Until a replacement/actual is known, fail closed.
            return EarningsEntryDecision(
                False,
                EarningsEntryReason.UNRESOLVED_EARNINGS_SCHEDULE,
                fill_session,
                hold_end,
                conflicting_event_key=schedule.event_key,
            )

        assert schedule.scheduled_session is not None
        event_date = schedule.scheduled_session
        post_event_at = _post_event_decision_at(calendar, event_date)

        if event_date < fill_session:
            if decision < post_event_at:
                return EarningsEntryDecision(
                    False,
                    EarningsEntryReason.REENTRY_BEFORE_POST_EVENT_CLOSE,
                    fill_session,
                    hold_end,
                    conflicting_event_key=schedule.event_key,
                    conflicting_event_session=event_date,
                )
            continue

        if fill_session <= event_date <= hold_end:
            return EarningsEntryDecision(
                False,
                EarningsEntryReason.EARNINGS_WITHIN_MINIMUM_HOLD,
                fill_session,
                hold_end,
                conflicting_event_key=schedule.event_key,
                conflicting_event_session=event_date,
            )

    return EarningsEntryDecision(
        True,
        EarningsEntryReason.CLEAR,
        fill_session,
        hold_end,
    )


def plan_existing_position_exit(
    *,
    schedule: EarningsScheduleRevision,
    calendar: ExchangeCalendar,
    decision_session: date,
    decision_at: datetime,
) -> EarningsExitPlan:
    """Plan the next earnings exit without rewriting a missed historical deadline.

    The initial strategy emits/refreshes targets after the validated close and
    executes in the next session's 10:00-10:30 ET window. Therefore a schedule
    first learned after the decision that could have targeted its required exit
    session is a late revision. The next available execution session is used and
    the exception remains observable.
    """

    decision = require_aware(decision_at, "decision_at")
    if schedule.available_at > decision:
        raise PointInTimeError("cannot plan an exit from a future earnings revision")
    if decision < calendar.decision_at(decision_session):
        raise DataContractError("exit planning cannot precede the session decision timestamp")

    next_execution = calendar.next_session(decision_session).session_date

    if schedule.status == EarningsScheduleStatus.WITHDRAWN or schedule.scheduled_session is None:
        return EarningsExitPlan(
            reason=EarningsExitReason.UNRESOLVED_SCHEDULE,
            required_exit_session=None,
            execution_session=next_execution,
            late_revision=False,
            operational_exception=True,
            event_key=schedule.event_key,
        )

    required = required_earnings_exit_session(calendar, schedule)
    if required < next_execution:
        return EarningsExitPlan(
            reason=EarningsExitReason.LATE_SCHEDULE_REVISION,
            required_exit_session=required,
            execution_session=next_execution,
            late_revision=True,
            operational_exception=True,
            event_key=schedule.event_key,
        )
    if required == next_execution:
        return EarningsExitPlan(
            reason=EarningsExitReason.SCHEDULED_EARNINGS,
            required_exit_session=required,
            execution_session=required,
            late_revision=False,
            operational_exception=False,
            event_key=schedule.event_key,
        )
    return EarningsExitPlan(
        reason=EarningsExitReason.NOT_DUE,
        required_exit_session=required,
        execution_session=required,
        late_revision=False,
        operational_exception=False,
        event_key=schedule.event_key,
    )

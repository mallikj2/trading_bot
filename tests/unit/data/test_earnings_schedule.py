from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from trading_bot.data.calendars import ExchangeCalendar
from trading_bot.data.contracts import EarningsTiming, ExchangeSession
from trading_bot.data.earnings import (
    EarningsCoverageObservation,
    EarningsEntryReason,
    EarningsExitReason,
    EarningsRevisionKind,
    EarningsScheduleRevision,
    EarningsScheduleStatus,
    evaluate_new_entry,
    latest_schedule_as_of,
    plan_existing_position_exit,
    required_earnings_exit_session,
    validate_revision_sequence,
)
from trading_bot.data.errors import DataContractError

UTC = timezone.utc


def dt(day: int, hour: int = 20, minute: int = 30) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=UTC)


def calendar() -> ExchangeCalendar:
    sessions = []
    current = date(2026, 7, 27)
    end = date(2026, 10, 30)
    while current <= end:
        if current.weekday() < 5:
            sessions.append(
                ExchangeSession(
                    calendar_id="XNYS",
                    calendar_version="test-v1",
                    session_date=current,
                    open_at=datetime(current.year, current.month, current.day, 13, 30, tzinfo=UTC),
                    close_at=datetime(current.year, current.month, current.day, 20, 0, tzinfo=UTC),
                )
            )
        current += timedelta(days=1)
    return ExchangeCalendar(sessions)


def revision(
    *,
    instrument_id,
    event_key="Q3-2026",
    scheduled_session=date(2026, 8, 19),
    timing=EarningsTiming.AMC,
    status=EarningsScheduleStatus.FORECAST,
    kind=EarningsRevisionKind.INITIAL,
    available_at=dt(3),
    revision_no=0,
) -> EarningsScheduleRevision:
    return EarningsScheduleRevision(
        instrument_id=instrument_id,
        event_key=event_key,
        fiscal_year=2026,
        fiscal_period="Q3",
        scheduled_session=scheduled_session,
        timing=timing,
        status=status,
        revision_kind=kind,
        available_at=available_at,
        ingested_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        revision=revision_no,
        source_snapshot_id=f"snapshot-{revision_no}",
        provider="synthetic",
        source_event_id="event-1",
    )


def coverage(instrument_id, *, covered_through=date(2026, 10, 30), available_at=dt(3)):
    return EarningsCoverageObservation(
        instrument_id=instrument_id,
        covered_through=covered_through,
        available_at=available_at,
        ingested_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        revision=0,
        source_snapshot_id="coverage-0",
        provider="synthetic",
        complete=True,
    )


def test_future_revision_is_invisible_to_earlier_decision():
    iid = uuid4()
    rows = [
        revision(instrument_id=iid, scheduled_session=date(2026, 8, 19), available_at=dt(3)),
        revision(
            instrument_id=iid,
            scheduled_session=date(2026, 8, 18),
            timing=EarningsTiming.BMO,
            status=EarningsScheduleStatus.CONFIRMED,
            kind=EarningsRevisionKind.DATE_AND_TIME_CHANGE,
            available_at=dt(10),
            revision_no=1,
        ),
    ]
    selected = latest_schedule_as_of(rows, event_key="Q3-2026", decision_at=dt(5))
    assert selected.revision == 0
    assert selected.scheduled_session == date(2026, 8, 19)


def test_latest_revision_is_visible_after_it_became_known():
    iid = uuid4()
    rows = [
        revision(instrument_id=iid, available_at=dt(3)),
        revision(
            instrument_id=iid,
            scheduled_session=date(2026, 8, 18),
            timing=EarningsTiming.BMO,
            status=EarningsScheduleStatus.CONFIRMED,
            kind=EarningsRevisionKind.DATE_AND_TIME_CHANGE,
            available_at=dt(10),
            revision_no=1,
        ),
    ]
    assert latest_schedule_as_of(rows, event_key="Q3-2026", decision_at=dt(10, 21)).revision == 1


def test_missing_forward_coverage_blocks_entry_even_when_no_event_rows_exist():
    iid = uuid4()
    result = evaluate_new_entry(
        instrument_id=iid,
        decision_session=date(2026, 8, 3),
        decision_at=dt(3),
        calendar=calendar(),
        revisions=[],
        coverage_observations=[],
        minimum_holding_sessions=10,
    )
    assert result.allowed is False
    assert result.reason == EarningsEntryReason.INSUFFICIENT_FORWARD_COVERAGE


def test_short_forward_coverage_blocks_entry():
    iid = uuid4()
    result = evaluate_new_entry(
        instrument_id=iid,
        decision_session=date(2026, 8, 3),
        decision_at=dt(3),
        calendar=calendar(),
        revisions=[],
        coverage_observations=[coverage(iid, covered_through=date(2026, 8, 7))],
        minimum_holding_sessions=10,
    )
    assert result.reason == EarningsEntryReason.INSUFFICIENT_FORWARD_COVERAGE


def test_event_inside_minimum_hold_blocks_entry():
    iid = uuid4()
    result = evaluate_new_entry(
        instrument_id=iid,
        decision_session=date(2026, 8, 3),
        decision_at=dt(3),
        calendar=calendar(),
        revisions=[revision(instrument_id=iid, scheduled_session=date(2026, 8, 12))],
        coverage_observations=[coverage(iid)],
        minimum_holding_sessions=10,
    )
    assert result.allowed is False
    assert result.reason == EarningsEntryReason.EARNINGS_WITHIN_MINIMUM_HOLD
    assert result.conflicting_event_session == date(2026, 8, 12)


def test_event_outside_minimum_hold_allows_entry():
    iid = uuid4()
    result = evaluate_new_entry(
        instrument_id=iid,
        decision_session=date(2026, 8, 3),
        decision_at=dt(3),
        calendar=calendar(),
        revisions=[revision(instrument_id=iid, scheduled_session=date(2026, 9, 1))],
        coverage_observations=[coverage(iid)],
        minimum_holding_sessions=10,
    )
    assert result.allowed is True
    assert result.reason == EarningsEntryReason.CLEAR


def test_withdrawn_date_is_unresolved_not_no_event():
    iid = uuid4()
    row = revision(
        instrument_id=iid,
        scheduled_session=None,
        status=EarningsScheduleStatus.WITHDRAWN,
        kind=EarningsRevisionKind.WITHDRAWAL,
    )
    result = evaluate_new_entry(
        instrument_id=iid,
        decision_session=date(2026, 8, 3),
        decision_at=dt(3),
        calendar=calendar(),
        revisions=[row],
        coverage_observations=[coverage(iid)],
    )
    assert result.reason == EarningsEntryReason.UNRESOLVED_EARNINGS_SCHEDULE


@pytest.mark.parametrize(
    ("timing", "expected"),
    [
        (EarningsTiming.BMO, date(2026, 8, 18)),
        (EarningsTiming.UNKNOWN, date(2026, 8, 18)),
        (EarningsTiming.DURING_SESSION, date(2026, 8, 18)),
        (EarningsTiming.AMC, date(2026, 8, 19)),
    ],
)
def test_phase01_exit_timing_mapping(timing, expected):
    iid = uuid4()
    row = revision(instrument_id=iid, timing=timing, scheduled_session=date(2026, 8, 19))
    assert required_earnings_exit_session(calendar(), row) == expected


def test_weekend_unknown_event_exits_prior_trading_session():
    iid = uuid4()
    row = revision(
        instrument_id=iid,
        timing=EarningsTiming.UNKNOWN,
        scheduled_session=date(2026, 8, 22),  # Saturday
    )
    assert required_earnings_exit_session(calendar(), row) == date(2026, 8, 21)


def test_amc_on_non_session_is_rejected():
    iid = uuid4()
    row = revision(
        instrument_id=iid,
        timing=EarningsTiming.AMC,
        scheduled_session=date(2026, 8, 22),
    )
    with pytest.raises(DataContractError):
        required_earnings_exit_session(calendar(), row)


def test_normal_bmo_exit_targets_required_next_session():
    iid = uuid4()
    row = revision(
        instrument_id=iid,
        timing=EarningsTiming.BMO,
        scheduled_session=date(2026, 8, 12),
        available_at=dt(10),
    )
    result = plan_existing_position_exit(
        schedule=row,
        calendar=calendar(),
        decision_session=date(2026, 8, 10),
        decision_at=dt(10),
    )
    assert result.reason == EarningsExitReason.SCHEDULED_EARNINGS
    assert result.execution_session == date(2026, 8, 11)
    assert result.late_revision is False


def test_late_bmo_revision_uses_next_available_window_without_rewriting_history():
    iid = uuid4()
    row = revision(
        instrument_id=iid,
        timing=EarningsTiming.BMO,
        status=EarningsScheduleStatus.CONFIRMED,
        kind=EarningsRevisionKind.TIME_CHANGE,
        scheduled_session=date(2026, 8, 12),
        available_at=dt(11),
        revision_no=1,
    )
    result = plan_existing_position_exit(
        schedule=row,
        calendar=calendar(),
        decision_session=date(2026, 8, 11),
        decision_at=dt(11),
    )
    assert result.reason == EarningsExitReason.LATE_SCHEDULE_REVISION
    assert result.required_exit_session == date(2026, 8, 11)
    assert result.execution_session == date(2026, 8, 12)
    assert result.operational_exception is True


def test_withdrawal_for_existing_position_forces_next_session_exit():
    iid = uuid4()
    row = revision(
        instrument_id=iid,
        scheduled_session=None,
        status=EarningsScheduleStatus.WITHDRAWN,
        kind=EarningsRevisionKind.WITHDRAWAL,
        available_at=dt(10),
    )
    result = plan_existing_position_exit(
        schedule=row,
        calendar=calendar(),
        decision_session=date(2026, 8, 10),
        decision_at=dt(10),
    )
    assert result.reason == EarningsExitReason.UNRESOLVED_SCHEDULE
    assert result.execution_session == date(2026, 8, 11)
    assert result.operational_exception is True


def test_revision_sequence_rejects_duplicate_availability_revision_key():
    iid = uuid4()
    row = revision(instrument_id=iid)
    duplicate = revision(instrument_id=iid)
    with pytest.raises(DataContractError):
        validate_revision_sequence([row, duplicate])


def test_revision_sequence_requires_strictly_increasing_revision_number():
    iid = uuid4()
    rows = [
        revision(instrument_id=iid, available_at=dt(3), revision_no=0),
        revision(
            instrument_id=iid,
            available_at=dt(4),
            revision_no=0,
            kind=EarningsRevisionKind.STATUS_CHANGE,
        ),
    ]
    with pytest.raises(DataContractError):
        validate_revision_sequence(rows)


def test_active_schedule_requires_event_date():
    iid = uuid4()
    with pytest.raises(DataContractError):
        revision(instrument_id=iid, scheduled_session=None)


def test_ingestion_cannot_precede_provider_availability():
    iid = uuid4()
    with pytest.raises(DataContractError):
        EarningsScheduleRevision(
            instrument_id=iid,
            event_key="Q3-2026",
            fiscal_year=2026,
            fiscal_period="Q3",
            scheduled_session=date(2026, 8, 19),
            timing=EarningsTiming.AMC,
            status=EarningsScheduleStatus.CONFIRMED,
            revision_kind=EarningsRevisionKind.INITIAL,
            available_at=datetime(2026, 8, 20, tzinfo=UTC),
            ingested_at=datetime(2026, 8, 19, tzinfo=UTC),
            revision=0,
            source_snapshot_id="s",
            provider="synthetic",
        )


def test_duplicate_schedule_key_fails_during_as_of_selection():
    iid = uuid4()
    rows = [revision(instrument_id=iid), revision(instrument_id=iid)]
    with pytest.raises(DataContractError):
        latest_schedule_as_of(rows, event_key="Q3-2026", decision_at=dt(5))


def test_coverage_from_multiple_providers_is_ambiguous_and_blocks():
    iid = uuid4()
    a = coverage(iid)
    b = EarningsCoverageObservation(
        instrument_id=iid,
        covered_through=date(2026, 10, 30),
        available_at=dt(4),
        ingested_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        revision=1,
        source_snapshot_id="coverage-b",
        provider="other-provider",
        complete=True,
    )
    with pytest.raises(DataContractError):
        evaluate_new_entry(
            instrument_id=iid,
            decision_session=date(2026, 8, 4),
            decision_at=dt(4),
            calendar=calendar(),
            revisions=[],
            coverage_observations=[a, b],
        )

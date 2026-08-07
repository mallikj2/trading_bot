from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from trading_bot.data.calendars import ExchangeCalendar
from trading_bot.data.contracts import EarningsTiming, ExchangeSession
from trading_bot.data.earnings import (
    EarningsCoverageObservation,
    EarningsEntryReason,
    EarningsRevisionKind,
    EarningsScheduleRevision,
    EarningsScheduleStatus,
    evaluate_new_entry,
    latest_schedule_as_of,
    plan_existing_position_exit,
    EarningsExitReason,
)

UTC = timezone.utc


def make_calendar() -> ExchangeCalendar:
    sessions = []
    current = date(2026, 8, 3)
    while current <= date(2026, 10, 30):
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


def test_later_date_revision_changes_future_decision_but_not_prior_decision():
    iid = uuid4()
    imported = datetime(2026, 9, 1, tzinfo=UTC)
    revisions = [
        EarningsScheduleRevision(
            instrument_id=iid,
            event_key="Q3-2026",
            fiscal_year=2026,
            fiscal_period="Q3",
            scheduled_session=date(2026, 8, 12),
            timing=EarningsTiming.AMC,
            status=EarningsScheduleStatus.FORECAST,
            revision_kind=EarningsRevisionKind.INITIAL,
            available_at=datetime(2026, 8, 3, 20, 5, tzinfo=UTC),
            ingested_at=imported,
            revision=0,
            source_snapshot_id="s0",
            provider="synthetic",
        ),
        EarningsScheduleRevision(
            instrument_id=iid,
            event_key="Q3-2026",
            fiscal_year=2026,
            fiscal_period="Q3",
            scheduled_session=date(2026, 9, 15),
            timing=EarningsTiming.AMC,
            status=EarningsScheduleStatus.CONFIRMED,
            revision_kind=EarningsRevisionKind.DATE_CHANGE,
            available_at=datetime(2026, 8, 5, 14, 0, tzinfo=UTC),
            ingested_at=imported,
            revision=1,
            source_snapshot_id="s1",
            provider="synthetic",
        ),
    ]
    coverage = [
        EarningsCoverageObservation(
            instrument_id=iid,
            covered_through=date(2026, 10, 30),
            available_at=datetime(2026, 8, 3, 20, 0, tzinfo=UTC),
            ingested_at=imported,
            revision=0,
            source_snapshot_id="c0",
            provider="synthetic",
        )
    ]
    cal = make_calendar()

    before_revision = evaluate_new_entry(
        instrument_id=iid,
        decision_session=date(2026, 8, 4),
        decision_at=datetime(2026, 8, 4, 20, 30, tzinfo=UTC),
        calendar=cal,
        revisions=revisions,
        coverage_observations=coverage,
        minimum_holding_sessions=10,
    )
    assert before_revision.reason == EarningsEntryReason.EARNINGS_WITHIN_MINIMUM_HOLD

    after_revision = evaluate_new_entry(
        instrument_id=iid,
        decision_session=date(2026, 8, 5),
        decision_at=datetime(2026, 8, 5, 20, 30, tzinfo=UTC),
        calendar=cal,
        revisions=revisions,
        coverage_observations=coverage,
        minimum_holding_sessions=10,
    )
    assert after_revision.reason == EarningsEntryReason.CLEAR

    historical = latest_schedule_as_of(
        revisions,
        event_key="Q3-2026",
        decision_at=datetime(2026, 8, 4, 20, 30, tzinfo=UTC),
    )
    assert historical.revision == 0
    assert historical.scheduled_session == date(2026, 8, 12)


def test_time_revision_from_amc_to_bmo_can_be_late_and_is_observable():
    iid = uuid4()
    row = EarningsScheduleRevision(
        instrument_id=iid,
        event_key="Q3-2026",
        fiscal_year=2026,
        fiscal_period="Q3",
        scheduled_session=date(2026, 8, 12),
        timing=EarningsTiming.BMO,
        status=EarningsScheduleStatus.CONFIRMED,
        revision_kind=EarningsRevisionKind.TIME_CHANGE,
        available_at=datetime(2026, 8, 11, 19, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 9, 1, tzinfo=UTC),
        revision=1,
        source_snapshot_id="late-time-change",
        provider="synthetic",
    )
    plan = plan_existing_position_exit(
        schedule=row,
        calendar=make_calendar(),
        decision_session=date(2026, 8, 11),
        decision_at=datetime(2026, 8, 11, 20, 30, tzinfo=UTC),
    )
    assert plan.reason == EarningsExitReason.LATE_SCHEDULE_REVISION
    assert plan.operational_exception
    assert plan.execution_session == date(2026, 8, 12)

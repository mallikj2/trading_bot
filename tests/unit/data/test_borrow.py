from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from trading_bot.data.borrow import (
    BorrowAccrualInput,
    BorrowAvailability,
    BorrowCoverageObservation,
    BorrowDifficulty,
    BorrowEligibilityReason,
    BorrowEvent,
    BorrowEventType,
    BorrowObservation,
    BorrowPolicy,
    BorrowSourceKind,
    accrue_borrow_fees,
    borrow_cost_bps,
    evaluate_short_entry,
    latest_borrow_observation_as_of,
    validate_borrow_coverage,
)
from trading_bot.data.errors import DataContractError, PointInTimeError

UTC = timezone.utc


def ts(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 8, day, hour, 0, tzinfo=UTC)


def obs(
    iid,
    *,
    available_at=ts(3),
    observed_at=ts(3, 11),
    expires_at=ts(4),
    revision=0,
    availability=BorrowAvailability.AVAILABLE,
    difficulty=BorrowDifficulty.EASY,
    rate=Decimal("0.03"),
    shares=1000,
    provider="synthetic",
    source_kind=BorrowSourceKind.MARKET_COMPOSITE,
):
    return BorrowObservation(
        instrument_id=iid,
        observed_at=observed_at,
        available_at=available_at,
        expires_at=expires_at,
        availability=availability,
        difficulty=difficulty,
        annual_fee_rate=rate,
        available_shares=shares,
        provider=provider,
        environment="research",
        source_kind=source_kind,
        source_snapshot_id=f"snap-{revision}",
        revision=revision,
    )


def policy(**kwargs):
    values = dict(
        approved_provider="synthetic",
        require_broker_specific=False,
        allow_hard_to_borrow=True,
        require_available_shares=True,
        max_annual_fee_rate=None,
    )
    values.update(kwargs)
    return BorrowPolicy(**values)


def test_future_revision_is_not_visible():
    iid = uuid4()
    rows = [
        obs(iid, revision=0),
        obs(iid, observed_at=ts(3, 15), available_at=ts(5), expires_at=ts(6), revision=1, rate=Decimal("0.20")),
    ]
    selected = latest_borrow_observation_as_of(rows, decision_at=ts(3, 20))
    assert selected.revision == 0
    assert selected.annual_fee_rate == Decimal("0.03")


def test_expired_observation_is_not_carried_forward():
    iid = uuid4()
    assert latest_borrow_observation_as_of([obs(iid)], decision_at=ts(4, 13)) is None


def test_conflicting_same_revision_fails_closed():
    iid = uuid4()
    one = obs(iid)
    two = BorrowObservation(
        instrument_id=iid,
        observed_at=one.observed_at,
        available_at=one.available_at,
        expires_at=one.expires_at,
        availability=one.availability,
        difficulty=one.difficulty,
        provider=one.provider,
        environment=one.environment,
        source_kind=one.source_kind,
        source_snapshot_id="other-snapshot",
        revision=one.revision,
        annual_fee_rate=Decimal("0.04"),
        available_shares=one.available_shares,
    )
    with pytest.raises(PointInTimeError):
        latest_borrow_observation_as_of([one, two], decision_at=ts(3, 20))


def test_regulatory_proxy_cannot_claim_available():
    iid = uuid4()
    with pytest.raises(DataContractError):
        obs(iid, source_kind=BorrowSourceKind.REGULATORY_PROXY)


def test_missing_rate_blocks_short_entry():
    iid = uuid4()
    result = evaluate_short_entry([obs(iid, rate=None)], decision_at=ts(3, 20), requested_shares=10, policy=policy())
    assert result.allowed is False
    assert result.reason == BorrowEligibilityReason.MISSING_RATE


def test_insufficient_quantity_blocks_short_entry():
    iid = uuid4()
    result = evaluate_short_entry([obs(iid, shares=9)], decision_at=ts(3, 20), requested_shares=10, policy=policy())
    assert result.reason == BorrowEligibilityReason.INSUFFICIENT_QUANTITY


def test_hard_to_borrow_policy_is_explicit():
    iid = uuid4()
    result = evaluate_short_entry(
        [obs(iid, difficulty=BorrowDifficulty.HARD)],
        decision_at=ts(3, 20),
        requested_shares=10,
        policy=policy(allow_hard_to_borrow=False),
    )
    assert result.reason == BorrowEligibilityReason.HARD_TO_BORROW_BLOCKED


def test_live_gate_requires_broker_specific_observation():
    iid = uuid4()
    result = evaluate_short_entry(
        [obs(iid)],
        decision_at=ts(3, 20),
        requested_shares=10,
        policy=policy(require_broker_specific=True),
    )
    assert result.reason == BorrowEligibilityReason.BROKER_SPECIFIC_REQUIRED


def test_recall_known_by_decision_blocks_entry_or_continuation():
    iid = uuid4()
    event = BorrowEvent(
        instrument_id=iid,
        event_type=BorrowEventType.RECALL,
        effective_at=ts(3, 18),
        available_at=ts(3, 18),
        provider="synthetic",
        environment="research",
        source_snapshot_id="recall-snap",
        event_id="recall-1",
    )
    result = evaluate_short_entry(
        [obs(iid)], decision_at=ts(3, 20), requested_shares=10, policy=policy(), events=[event]
    )
    assert result.reason == BorrowEligibilityReason.ACTIVE_RECALL_OR_RESTRICTION
    assert result.blocking_event is event


def test_future_recall_does_not_leak_backward():
    iid = uuid4()
    event = BorrowEvent(
        instrument_id=iid,
        event_type=BorrowEventType.RECALL,
        effective_at=ts(5),
        available_at=ts(5),
        provider="synthetic",
        environment="research",
        source_snapshot_id="recall-snap",
        event_id="recall-1",
    )
    result = evaluate_short_entry(
        [obs(iid)], decision_at=ts(3, 20), requested_shares=10, policy=policy(), events=[event]
    )
    assert result.allowed is True


def test_rate_ceiling_blocks_uneconomic_borrow():
    iid = uuid4()
    result = evaluate_short_entry(
        [obs(iid, rate=Decimal("0.30"))],
        decision_at=ts(3, 20),
        requested_shares=10,
        policy=policy(max_annual_fee_rate=Decimal("0.10")),
    )
    assert result.reason == BorrowEligibilityReason.RATE_ABOVE_POLICY


def test_schwab_style_fee_formula_and_phase01_two_x_stress():
    rows = [
        BorrowAccrualInput(
            session_date=date(2026, 8, 7),
            end_of_day_short_market_value=Decimal("1000"),
            annual_fee_rate=Decimal("0.36"),
            calendar_days=3,
            source_snapshot_ids=("rate-fri", "price-fri"),
        )
    ]
    result = accrue_borrow_fees(rows, stress_multiplier=Decimal("2"))
    assert result.base_fee_usd == Decimal("3")
    assert result.stressed_fee_usd == Decimal("6")
    assert result.total_calendar_days == 3
    assert borrow_cost_bps(fee_usd=result.base_fee_usd, entry_notional_usd=Decimal("1000")) == Decimal("30")


def test_dense_coverage_must_be_explicit_before_absence_has_meaning():
    iid = uuid4()
    coverage = BorrowCoverageObservation(
        instrument_id=iid,
        covered_from=date(2026, 8, 1),
        covered_through=date(2026, 8, 31),
        available_at=ts(3),
        provider="synthetic",
        source_snapshot_id="coverage",
        complete_daily_coverage=True,
    )
    assert validate_borrow_coverage(
        [coverage],
        instrument_id=iid,
        session_date=date(2026, 8, 3),
        decision_at=ts(3, 20),
        provider="synthetic",
    )


def test_sparse_coverage_cannot_turn_missing_row_into_unavailable():
    iid = uuid4()
    coverage = BorrowCoverageObservation(
        instrument_id=iid,
        covered_from=date(2026, 8, 1),
        covered_through=date(2026, 8, 31),
        available_at=ts(3),
        provider="synthetic",
        source_snapshot_id="coverage",
        complete_daily_coverage=False,
    )
    assert not validate_borrow_coverage(
        [coverage],
        instrument_id=iid,
        session_date=date(2026, 8, 3),
        decision_at=ts(3, 20),
        provider="synthetic",
    )


def test_existing_short_exits_when_borrow_record_expires():
    from trading_bot.data.borrow import evaluate_existing_short

    iid = uuid4()
    result = evaluate_existing_short(
        [obs(iid)],
        decision_at=ts(4, 13),
        current_shares=10,
        policy=policy(),
    )
    assert result.exit_required is True
    assert result.reason == BorrowEligibilityReason.EXPIRED_OBSERVATION


def test_known_future_effective_recall_blocks_immediately():
    iid = uuid4()
    event = BorrowEvent(
        instrument_id=iid,
        event_type=BorrowEventType.RECALL,
        effective_at=ts(5),
        available_at=ts(3, 18),
        provider="synthetic",
        environment="research",
        source_snapshot_id="recall-known",
        event_id="recall-known-1",
    )
    result = evaluate_short_entry(
        [obs(iid)], decision_at=ts(3, 20), requested_shares=10, policy=policy(), events=[event]
    )
    assert result.reason == BorrowEligibilityReason.ACTIVE_RECALL_OR_RESTRICTION


def test_available_to_unavailable_transition_creates_withdrawal_event():
    from trading_bot.data.borrow import derive_availability_withdrawal_events

    iid = uuid4()
    first = obs(iid, expires_at=ts(4), revision=0)
    second = obs(
        iid,
        observed_at=ts(4, 11),
        available_at=ts(4, 12),
        expires_at=ts(5),
        revision=1,
        availability=BorrowAvailability.UNAVAILABLE,
        rate=None,
        shares=0,
    )
    events = derive_availability_withdrawal_events([first, second])
    assert len(events) == 1
    assert events[0].event_type == BorrowEventType.AVAILABILITY_WITHDRAWN
    assert events[0].available_at == second.available_at

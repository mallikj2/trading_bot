from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from trading_bot.data.borrow import (
    BorrowAccrualInput,
    BorrowAvailability,
    BorrowDifficulty,
    BorrowObservation,
    BorrowPolicy,
    BorrowSourceKind,
    accrue_borrow_fees,
    evaluate_short_entry,
)

UTC = timezone.utc


def test_research_short_requires_known_borrow_and_cost_is_explicit():
    iid = uuid4()
    decision = datetime(2026, 8, 3, 20, 30, tzinfo=UTC)
    observation = BorrowObservation(
        instrument_id=iid,
        observed_at=datetime(2026, 8, 3, 11, 30, tzinfo=UTC),
        available_at=datetime(2026, 8, 3, 11, 30, tzinfo=UTC),
        expires_at=datetime(2026, 8, 4, 11, 30, tzinfo=UTC),
        availability=BorrowAvailability.AVAILABLE,
        difficulty=BorrowDifficulty.EASY,
        annual_fee_rate=Decimal("0.05"),
        available_shares=500,
        provider="approved-research-source",
        environment="research",
        source_kind=BorrowSourceKind.MARKET_COMPOSITE,
        source_snapshot_id="borrow-snapshot",
    )
    gate = evaluate_short_entry(
        [observation],
        decision_at=decision,
        requested_shares=20,
        policy=BorrowPolicy(
            approved_provider="approved-research-source",
            require_broker_specific=False,
            allow_hard_to_borrow=True,
            require_available_shares=True,
        ),
    )
    assert gate.allowed is True

    accrual = accrue_borrow_fees(
        [
            BorrowAccrualInput(
                session_date=date(2026, 8, 4),
                end_of_day_short_market_value=Decimal("2000"),
                annual_fee_rate=observation.annual_fee_rate,
                calendar_days=1,
                source_snapshot_ids=(observation.source_snapshot_id, "price-snapshot"),
            )
        ],
        stress_multiplier=Decimal("2"),
    )
    assert accrual.base_fee_usd > 0
    assert accrual.stressed_fee_usd == accrual.base_fee_usd * 2


def test_live_short_cannot_reuse_market_composite_research_evidence():
    iid = uuid4()
    decision = datetime(2026, 8, 3, 20, 30, tzinfo=UTC)
    row = BorrowObservation(
        instrument_id=iid,
        observed_at=datetime(2026, 8, 3, 11, 30, tzinfo=UTC),
        available_at=datetime(2026, 8, 3, 11, 30, tzinfo=UTC),
        expires_at=datetime(2026, 8, 4, 11, 30, tzinfo=UTC),
        availability=BorrowAvailability.AVAILABLE,
        difficulty=BorrowDifficulty.EASY,
        annual_fee_rate=Decimal("0.01"),
        available_shares=10000,
        provider="market-composite",
        environment="research",
        source_kind=BorrowSourceKind.MARKET_COMPOSITE,
        source_snapshot_id="snap",
    )
    gate = evaluate_short_entry(
        [row],
        decision_at=decision,
        requested_shares=1,
        policy=BorrowPolicy(
            approved_provider="market-composite",
            require_broker_specific=True,
            allow_hard_to_borrow=False,
            require_available_shares=True,
        ),
    )
    assert gate.allowed is False

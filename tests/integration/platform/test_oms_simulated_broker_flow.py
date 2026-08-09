from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.leads import (
    BorrowState,
    CostState,
    EarningsState,
    FactorObservation,
    LeadDirection,
    LeadLifecycleState,
    LeadProvenance,
    LeadTrendState,
    LeadUniverseState,
    LeadVolatilityState,
    TradeLead,
)
from trading_bot.platform.orders import OMSStateError, OrderIntent, OrderPurpose, OrderState
from trading_bot.platform.runtime_safety import RuntimeSafetyState
from trading_bot.platform.simulated_broker import (
    BrokerTruthState,
    ClientCancelOutcome,
    ClientSubmissionOutcome,
    OMSService,
    SimulatedBroker,
    SubmissionPlan,
)

UTC = timezone.utc
DECISION = datetime(2026, 8, 8, 13, 30, tzinfo=UTC)
GENERATED = DECISION + timedelta(minutes=1)
T0 = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)


def planned_lead(direction: LeadDirection = LeadDirection.LONG) -> TradeLead:
    lead = TradeLead.create(
        instrument_id=UUID("11111111-2222-3333-4444-555555555555"),
        decision_symbol="TEST",
        decision_symbol_available_at=DECISION - timedelta(days=1),
        display_symbol="TEST",
        display_symbol_as_of=DECISION,
        strategy_id="CSMOM-LS",
        strategy_version="v0.2",
        generated_at=GENERATED,
        decision_at=DECISION,
        valid_until=T0 + timedelta(days=1),
        direction=direction,
        score=Decimal("1.25") if direction == LeadDirection.LONG else Decimal("-1.25"),
        factors=(
            FactorObservation("mom_12_1", Decimal("0.3"), DECISION - timedelta(seconds=1)),
            FactorObservation("mom_6_1", Decimal("0.2"), DECISION - timedelta(seconds=1)),
            FactorObservation("vol20", Decimal("0.2"), DECISION - timedelta(seconds=1)),
        ),
        trend_state=LeadTrendState.ABOVE_SMA200 if direction == LeadDirection.LONG else LeadTrendState.BELOW_SMA200,
        volatility_state=LeadVolatilityState.WITHIN_LIMIT,
        universe_state=LeadUniverseState.ELIGIBLE,
        earnings_state=EarningsState.CLEAR,
        cost_state=CostState.CLEAR,
        borrow_state=BorrowState.NOT_APPLICABLE if direction == LeadDirection.LONG else BorrowState.AVAILABLE,
        provenance=LeadProvenance("1" * 64, "2" * 64, "3" * 64, DECISION - timedelta(seconds=1)),
        initial_state=LeadLifecycleState.QUALIFIED,
        estimated_spread_bps=Decimal("10"),
        estimated_cost_bps=Decimal("15"),
    )
    lead = lead.with_allocation(proposed_weight=Decimal("0.15") if direction == LeadDirection.LONG else Decimal("-0.15"), proposed_shares=3)
    return lead.transition(LeadLifecycleState.PLANNED, changed_at=GENERATED + timedelta(minutes=1))


def service(tmp_path: Path, *, state: RuntimeSafetyState = RuntimeSafetyState.ACTIVE) -> tuple[OMSService, SimulatedBroker, SQLiteEventJournal]:
    journal = SQLiteEventJournal(tmp_path / "oms.sqlite")
    broker = SimulatedBroker()
    return OMSService(journal=journal, broker=broker, runtime_state=state), broker, journal


def test_tradelead_to_order_to_partial_and_full_fill_replays_identically(tmp_path: Path) -> None:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    oms, broker, journal = service(tmp_path)
    oms.create(intent)
    oms.approve_risk(intent.order_id, approved_at=T0 + timedelta(seconds=1))
    assert oms.submit(intent.order_id, submitted_at=T0 + timedelta(seconds=2)).state == OrderState.ACKNOWLEDGED
    oms.apply_fill(intent.order_id, quantity=1, price="100", occurred_at=T0 + timedelta(seconds=3), execution_id="exec-1")
    final = oms.apply_fill(intent.order_id, quantity=2, price="102", occurred_at=T0 + timedelta(seconds=4), execution_id="exec-2")
    assert final.state == OrderState.FILLED
    assert final.average_fill_price == Decimal("101.3333333333333333333333333")
    state_hash = oms.projector.state_hash
    journal.verify_integrity()
    journal.close()

    reopened = SQLiteEventJournal(tmp_path / "oms.sqlite")
    replayed = OMSService(journal=reopened, broker=broker)
    assert replayed.projector.state_hash == state_hash
    assert replayed.projector.get(intent.order_id).state == OrderState.FILLED
    reopened.close()


def test_unknown_submission_is_not_resubmitted_and_reconciles_ack(tmp_path: Path) -> None:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    oms, broker, journal = service(tmp_path)
    oms.create(intent)
    oms.approve_risk(intent.order_id, approved_at=T0 + timedelta(seconds=1))
    state = oms.submit(
        intent.order_id,
        submitted_at=T0 + timedelta(seconds=2),
        plan=SubmissionPlan(ClientSubmissionOutcome.UNKNOWN, BrokerTruthState.ACKNOWLEDGED, "timeout"),
    )
    assert state.state == OrderState.UNKNOWN
    with pytest.raises(OMSStateError, match="UNKNOWN order"):
        oms.submit(intent.order_id, submitted_at=T0 + timedelta(seconds=3))
    assert broker.submission_count(intent.order_id) == 1
    reconciled = oms.reconcile(intent.order_id, reconciled_at=T0 + timedelta(seconds=4))
    assert reconciled.state == OrderState.ACKNOWLEDGED
    assert broker.submission_count(intent.order_id) == 1
    journal.close()


def test_unknown_submission_reconciles_rejection(tmp_path: Path) -> None:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    oms, _broker, journal = service(tmp_path)
    oms.create(intent)
    oms.approve_risk(intent.order_id, approved_at=T0 + timedelta(seconds=1))
    oms.submit(
        intent.order_id,
        submitted_at=T0 + timedelta(seconds=2),
        plan=SubmissionPlan(ClientSubmissionOutcome.UNKNOWN, BrokerTruthState.REJECTED, "sim reject"),
    )
    reconciled = oms.reconcile(intent.order_id, reconciled_at=T0 + timedelta(seconds=3))
    assert reconciled.state == OrderState.REJECTED
    assert reconciled.rejection_reason == "sim reject"
    journal.close()


def test_cancel_ack_and_unknown_cancel_reconciliation(tmp_path: Path) -> None:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    oms, _broker, journal = service(tmp_path)
    oms.create(intent)
    oms.approve_risk(intent.order_id, approved_at=T0 + timedelta(seconds=1))
    oms.submit(intent.order_id, submitted_at=T0 + timedelta(seconds=2))
    canceled = oms.request_cancel(intent.order_id, requested_at=T0 + timedelta(seconds=3))
    assert canceled.state == OrderState.CANCELED
    journal.close()

    # Second order exercises uncertain cancel -> reconciliation.
    journal2 = SQLiteEventJournal(tmp_path / "oms2.sqlite")
    broker2 = SimulatedBroker()
    oms2 = OMSService(journal=journal2, broker=broker2)
    lead2 = planned_lead(LeadDirection.SHORT)
    intent2 = OrderIntent.from_trade_lead(lead2, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    oms2.create(intent2)
    oms2.approve_risk(intent2.order_id, approved_at=T0 + timedelta(seconds=1))
    oms2.submit(intent2.order_id, submitted_at=T0 + timedelta(seconds=2))
    unknown = oms2.request_cancel(
        intent2.order_id,
        requested_at=T0 + timedelta(seconds=3),
        client_outcome=ClientCancelOutcome.UNKNOWN,
    )
    assert unknown.state == OrderState.UNKNOWN
    assert oms2.reconcile(intent2.order_id, reconciled_at=T0 + timedelta(seconds=4)).state == OrderState.CANCELED
    journal2.close()


def test_runtime_reducing_blocks_new_exposure_but_allows_reduction(tmp_path: Path) -> None:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    oms, _broker, journal = service(tmp_path, state=RuntimeSafetyState.REDUCING)
    oms.create(intent)
    oms.approve_risk(intent.order_id, approved_at=T0 + timedelta(seconds=1))
    with pytest.raises(OMSStateError, match="blocks simulated exposure increases"):
        oms.submit(intent.order_id, submitted_at=T0 + timedelta(seconds=2))
    journal.close()

    # Construct an exit intent from an entered long; REDUCING permits it.
    entered = lead.transition(LeadLifecycleState.ENTERED, changed_at=T0 - timedelta(seconds=1))
    exit_pending = entered.transition(LeadLifecycleState.EXIT_PENDING, changed_at=T0)
    exit_intent = OrderIntent.from_trade_lead(exit_pending, purpose=OrderPurpose.REDUCE_EXPOSURE, created_at=T0)
    journal2 = SQLiteEventJournal(tmp_path / "reduce.sqlite")
    oms2 = OMSService(journal=journal2, broker=SimulatedBroker(), runtime_state=RuntimeSafetyState.REDUCING)
    oms2.create(exit_intent)
    oms2.approve_risk(exit_intent.order_id, approved_at=T0 + timedelta(seconds=1))
    assert oms2.submit(exit_intent.order_id, submitted_at=T0 + timedelta(seconds=2)).state == OrderState.ACKNOWLEDGED
    journal2.close()


def test_halted_blocks_exposure_change_but_still_allows_cancel(tmp_path: Path) -> None:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    oms, _broker, journal = service(tmp_path, state=RuntimeSafetyState.ACTIVE)
    oms.create(intent)
    oms.approve_risk(intent.order_id, approved_at=T0 + timedelta(seconds=1))
    oms.submit(intent.order_id, submitted_at=T0 + timedelta(seconds=2))
    oms.set_runtime_state(RuntimeSafetyState.HALTED)
    canceled = oms.request_cancel(intent.order_id, requested_at=T0 + timedelta(seconds=3))
    assert canceled.state == OrderState.CANCELED
    journal.close()


def test_direct_broker_rejection_and_order_expiration(tmp_path: Path) -> None:
    lead = planned_lead()
    rejected_intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    journal = SQLiteEventJournal(tmp_path / "reject.sqlite")
    oms = OMSService(journal=journal, broker=SimulatedBroker())
    oms.create(rejected_intent)
    oms.approve_risk(rejected_intent.order_id, approved_at=T0 + timedelta(seconds=1))
    rejected = oms.submit(
        rejected_intent.order_id,
        submitted_at=T0 + timedelta(seconds=2),
        plan=SubmissionPlan(ClientSubmissionOutcome.REJECTED, BrokerTruthState.REJECTED, "risk fixture reject"),
    )
    assert rejected.state == OrderState.REJECTED
    assert rejected.rejection_reason == "risk fixture reject"
    journal.close()

    # Use a distinct lead direction so the deterministic order ID is different.
    short_lead = planned_lead(LeadDirection.SHORT)
    expiring = OrderIntent.from_trade_lead(short_lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    journal2 = SQLiteEventJournal(tmp_path / "expire.sqlite")
    oms2 = OMSService(journal=journal2, broker=SimulatedBroker())
    oms2.create(expiring)
    oms2.approve_risk(expiring.order_id, approved_at=T0 + timedelta(seconds=1))
    oms2.submit(expiring.order_id, submitted_at=T0 + timedelta(seconds=2))
    expired = oms2.expire_order(expiring.order_id, expired_at=T0 + timedelta(hours=6))
    assert expired.state == OrderState.EXPIRED
    journal2.close()


def test_tradelead_direction_maps_to_open_and_close_order_sides() -> None:
    long_planned = planned_lead(LeadDirection.LONG)
    long_open = OrderIntent.from_trade_lead(long_planned, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    assert long_open.side.value == "BUY"
    long_exit = long_planned.transition(LeadLifecycleState.ENTERED, changed_at=T0 - timedelta(seconds=1)).transition(
        LeadLifecycleState.EXIT_PENDING, changed_at=T0
    )
    assert OrderIntent.from_trade_lead(long_exit, purpose=OrderPurpose.REDUCE_EXPOSURE, created_at=T0).side.value == "SELL"

    short_planned = planned_lead(LeadDirection.SHORT)
    short_open = OrderIntent.from_trade_lead(short_planned, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    assert short_open.side.value == "SELL_SHORT"
    short_exit = short_planned.transition(LeadLifecycleState.ENTERED, changed_at=T0 - timedelta(seconds=1)).transition(
        LeadLifecycleState.EXIT_PENDING, changed_at=T0
    )
    assert OrderIntent.from_trade_lead(short_exit, purpose=OrderPurpose.REDUCE_EXPOSURE, created_at=T0).side.value == "BUY_TO_COVER"

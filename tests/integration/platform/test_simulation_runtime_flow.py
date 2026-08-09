from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.leads import (
    BorrowState, CostState, EarningsState, FactorObservation, LeadDirection,
    LeadLifecycleState, LeadProvenance, LeadTrendState, LeadUniverseState,
    LeadVolatilityState, TradeLead,
)
from trading_bot.platform.orders import OrderIntent, OrderPurpose
from trading_bot.platform.simulation_runtime import SimulationCommand, SimulationCommandKind, SimulationPlan, SimulationRuntime

UTC = timezone.utc
START = datetime(2026, 8, 8, 13, 30, tzinfo=UTC)
T0 = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)
END = datetime(2026, 8, 8, 16, 0, tzinfo=UTC)


def lead(direction: LeadDirection) -> TradeLead:
    generated = START + timedelta(minutes=1)
    value = Decimal("1.1") if direction == LeadDirection.LONG else Decimal("-1.1")
    item = TradeLead.create(
        instrument_id=UUID("11111111-2222-3333-4444-555555555555") if direction == LeadDirection.LONG else UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        decision_symbol="LONG" if direction == LeadDirection.LONG else "SHORT",
        decision_symbol_available_at=START - timedelta(days=1),
        display_symbol="LONG" if direction == LeadDirection.LONG else "SHORT",
        display_symbol_as_of=START,
        strategy_id="CSMOM-LS", strategy_version="v0.2",
        generated_at=generated, decision_at=START, valid_until=END + timedelta(days=1),
        direction=direction, score=value,
        factors=(FactorObservation("mom_12_1", value, START - timedelta(seconds=1)),),
        trend_state=LeadTrendState.ABOVE_SMA200 if direction == LeadDirection.LONG else LeadTrendState.BELOW_SMA200,
        volatility_state=LeadVolatilityState.WITHIN_LIMIT,
        universe_state=LeadUniverseState.ELIGIBLE,
        earnings_state=EarningsState.CLEAR, cost_state=CostState.CLEAR,
        borrow_state=BorrowState.NOT_APPLICABLE if direction == LeadDirection.LONG else BorrowState.AVAILABLE,
        provenance=LeadProvenance("1"*64, "2"*64, "3"*64, START - timedelta(seconds=1)),
        initial_state=LeadLifecycleState.QUALIFIED,
        estimated_spread_bps=Decimal("9"), estimated_cost_bps=Decimal("14"),
    )
    item = item.with_allocation(proposed_weight=Decimal("0.15") if direction == LeadDirection.LONG else Decimal("-0.15"), proposed_shares=2)
    return item.transition(LeadLifecycleState.PLANNED, changed_at=generated + timedelta(minutes=1))


def cmd(n, at, kind, payload):
    return SimulationCommand.create(ordinal=n, at=at, kind=kind, payload=payload)


def two_order_plan() -> SimulationPlan:
    long = lead(LeadDirection.LONG)
    short = lead(LeadDirection.SHORT)
    long_order = OrderIntent.from_trade_lead(long, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    short_t = T0 + timedelta(minutes=30)
    short_order = OrderIntent.from_trade_lead(short, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=short_t)
    commands = [
        cmd(1, START + timedelta(minutes=2), SimulationCommandKind.LEAD_SNAPSHOT, {"lead": long.to_dict()}),
        cmd(2, T0, SimulationCommandKind.OMS_CREATE, {"intent": long_order.to_dict()}),
        cmd(3, T0 + timedelta(seconds=1), SimulationCommandKind.OMS_RISK_APPROVE, {"order_id": long_order.order_id}),
        cmd(4, T0 + timedelta(seconds=2), SimulationCommandKind.OMS_SUBMIT, {"order_id": long_order.order_id}),
        cmd(5, T0 + timedelta(seconds=3), SimulationCommandKind.OMS_FILL, {"order_id": long_order.order_id, "quantity": 2, "price": "100", "execution_id": "long-e1"}),
        cmd(6, T0 + timedelta(minutes=15), SimulationCommandKind.LEAD_SNAPSHOT, {"lead": short.to_dict()}),
        cmd(7, short_t, SimulationCommandKind.OMS_CREATE, {"intent": short_order.to_dict()}),
        cmd(8, short_t + timedelta(seconds=1), SimulationCommandKind.OMS_RISK_APPROVE, {"order_id": short_order.order_id}),
        cmd(9, short_t + timedelta(seconds=2), SimulationCommandKind.OMS_SUBMIT, {"order_id": short_order.order_id}),
        cmd(10, short_t + timedelta(seconds=3), SimulationCommandKind.OMS_FILL, {"order_id": short_order.order_id, "quantity": 2, "price": "50", "execution_id": "short-e1"}),
    ]
    return SimulationPlan.create(name="two-order-session", started_at=START, ends_at=END, commands=commands)


def test_quiescent_restart_matches_uninterrupted_session_exactly(tmp_path) -> None:
    plan = two_order_plan()

    uninterrupted_path = tmp_path / "uninterrupted.sqlite"
    journal = SQLiteEventJournal(uninterrupted_path)
    try:
        uninterrupted = SimulationRuntime(journal=journal).run(plan)
    finally:
        journal.close()

    restarted_path = tmp_path / "restarted.sqlite"
    journal = SQLiteEventJournal(restarted_path)
    try:
        partial = SimulationRuntime(journal=journal).run(plan, through_ordinal=5)
        assert partial.status == "IN_PROGRESS"
        assert partial.applied_commands == 5
    finally:
        journal.close()

    reopened = SQLiteEventJournal(restarted_path)
    try:
        restarted = SimulationRuntime(journal=reopened).run(plan)
    finally:
        reopened.close()

    assert restarted.status == "COMPLETED"
    assert restarted.applied_commands == 10
    assert restarted.journal_event_count == uninterrupted.journal_event_count
    assert restarted.journal_head_hash == uninterrupted.journal_head_hash
    assert restarted.lead_state_hash == uninterrupted.lead_state_hash
    assert restarted.order_state_hash == uninterrupted.order_state_hash
    assert restarted.composite_state_hash == uninterrupted.composite_state_hash


def test_simulation_journal_contains_leads_orders_clock_and_session_events(tmp_path) -> None:
    plan = two_order_plan()
    journal = SQLiteEventJournal(tmp_path / "session.sqlite")
    try:
        result = SimulationRuntime(journal=journal).run(plan)
        types = {record.event.event_type for record in journal.records()}
        assert result.status == "COMPLETED"
        assert "SIMULATION.SESSION_STARTED" in types
        assert "SIMULATION.CLOCK_ADVANCED" in types
        assert "SIMULATION.COMMAND_APPLIED" in types
        assert "SIMULATION.SESSION_COMPLETED" in types
        assert "TRADE_LEAD.SNAPSHOT" in types
        assert "OMS.ORDER_CREATED" in types
        assert "OMS.ORDER_FILLED" in types
        assert journal.verify_integrity() == result.journal_head_hash
    finally:
        journal.close()

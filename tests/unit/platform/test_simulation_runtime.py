from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.leads import (
    BorrowState, CostState, EarningsState, FactorObservation, LeadDirection,
    LeadLifecycleState, LeadProvenance, LeadTrendState, LeadUniverseState,
    LeadVolatilityState, TradeLead,
)
from trading_bot.platform.orders import OrderIntent, OrderPurpose
from trading_bot.platform.simulation_runtime import (
    DeterministicClock, SimulationCommand, SimulationCommandKind,
    SimulationContractError, SimulationPlan, SimulationRuntime, SimulationRuntimeError,
)

UTC = timezone.utc
START = datetime(2026, 8, 8, 13, 30, tzinfo=UTC)
T0 = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)
END = datetime(2026, 8, 8, 15, 0, tzinfo=UTC)


def planned_lead(direction: LeadDirection = LeadDirection.LONG) -> TradeLead:
    generated = START + timedelta(minutes=1)
    lead = TradeLead.create(
        instrument_id=UUID("11111111-2222-3333-4444-555555555555"),
        decision_symbol="TEST",
        decision_symbol_available_at=START - timedelta(days=1),
        display_symbol="TEST",
        display_symbol_as_of=START,
        strategy_id="CSMOM-LS",
        strategy_version="v0.2",
        generated_at=generated,
        decision_at=START,
        valid_until=END + timedelta(days=1),
        direction=direction,
        score=Decimal("1.25") if direction == LeadDirection.LONG else Decimal("-1.25"),
        factors=(
            FactorObservation("mom_12_1", Decimal("0.3"), START - timedelta(seconds=1)),
            FactorObservation("mom_6_1", Decimal("0.2"), START - timedelta(seconds=1)),
            FactorObservation("vol20", Decimal("0.2"), START - timedelta(seconds=1)),
        ),
        trend_state=LeadTrendState.ABOVE_SMA200 if direction == LeadDirection.LONG else LeadTrendState.BELOW_SMA200,
        volatility_state=LeadVolatilityState.WITHIN_LIMIT,
        universe_state=LeadUniverseState.ELIGIBLE,
        earnings_state=EarningsState.CLEAR,
        cost_state=CostState.CLEAR,
        borrow_state=BorrowState.NOT_APPLICABLE if direction == LeadDirection.LONG else BorrowState.AVAILABLE,
        provenance=LeadProvenance("1" * 64, "2" * 64, "3" * 64, START - timedelta(seconds=1)),
        initial_state=LeadLifecycleState.QUALIFIED,
        estimated_spread_bps=Decimal("10"),
        estimated_cost_bps=Decimal("15"),
    )
    lead = lead.with_allocation(
        proposed_weight=Decimal("0.15") if direction == LeadDirection.LONG else Decimal("-0.15"),
        proposed_shares=3,
    )
    return lead.transition(LeadLifecycleState.PLANNED, changed_at=generated + timedelta(minutes=1))


def command(ordinal: int, at: datetime, kind: SimulationCommandKind, payload: dict) -> SimulationCommand:
    return SimulationCommand.create(ordinal=ordinal, at=at, kind=kind, payload=payload)


def single_order_plan(*, include_fill: bool = True) -> SimulationPlan:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    commands = [
        command(1, START + timedelta(minutes=2), SimulationCommandKind.LEAD_SNAPSHOT, {"lead": lead.to_dict()}),
        command(2, T0, SimulationCommandKind.OMS_CREATE, {"intent": intent.to_dict()}),
        command(3, T0 + timedelta(seconds=1), SimulationCommandKind.OMS_RISK_APPROVE, {"order_id": intent.order_id}),
        command(4, T0 + timedelta(seconds=2), SimulationCommandKind.OMS_SUBMIT, {"order_id": intent.order_id}),
    ]
    if include_fill:
        commands.append(command(5, T0 + timedelta(seconds=3), SimulationCommandKind.OMS_FILL, {
            "order_id": intent.order_id, "quantity": 3, "price": "101.25", "execution_id": "exec-1"
        }))
    return SimulationPlan.create(name="single-order", started_at=START, ends_at=END, commands=commands)


def test_deterministic_clock_never_uses_wall_clock_or_moves_backward() -> None:
    clock = DeterministicClock(START, START, END)
    assert clock.advance_to(T0).current_at == T0
    with pytest.raises(SimulationRuntimeError, match="backward"):
        clock.advance_to(START - timedelta(seconds=1))
    with pytest.raises(SimulationRuntimeError, match="session end"):
        clock.advance_to(END + timedelta(seconds=1))


def test_command_and_plan_identity_roundtrip_is_deterministic() -> None:
    plan = single_order_plan()
    assert SimulationPlan.from_dict(plan.to_dict()) == plan
    recreated = single_order_plan()
    assert recreated.plan_id == plan.plan_id
    assert [c.command_id for c in recreated.commands] == [c.command_id for c in plan.commands]


def test_plan_rejects_out_of_order_commands() -> None:
    c1 = command(1, T0, SimulationCommandKind.OMS_CANCEL, {"order_id": "x"})
    c2 = command(2, START, SimulationCommandKind.OMS_CANCEL, {"order_id": "x"})
    with pytest.raises(SimulationContractError, match="ordered by timestamp"):
        SimulationPlan.create(name="bad", started_at=START, ends_at=END, commands=[c1, c2])


def test_identical_sessions_have_identical_journal_and_composite_hash(tmp_path) -> None:
    plan = single_order_plan()
    results = []
    for name in ("a.sqlite", "b.sqlite"):
        journal = SQLiteEventJournal(tmp_path / name)
        try:
            result = SimulationRuntime(journal=journal).run(plan)
            results.append(result)
        finally:
            journal.close()
    assert results[0].status == "COMPLETED"
    assert results[0].journal_head_hash == results[1].journal_head_hash
    assert results[0].composite_state_hash == results[1].composite_state_hash
    assert results[0].order_state_hash == results[1].order_state_hash
    assert results[0].lead_state_hash == results[1].lead_state_hash


def test_completed_plan_rerun_is_idempotent(tmp_path) -> None:
    plan = single_order_plan()
    journal = SQLiteEventJournal(tmp_path / "idempotent.sqlite")
    try:
        runtime = SimulationRuntime(journal=journal)
        first = runtime.run(plan)
        count = len(journal.records())
        second = runtime.run(plan)
        assert len(journal.records()) == count
        assert first == second
    finally:
        journal.close()


def test_restart_with_open_order_is_explicitly_deferred_to_pf10(tmp_path) -> None:
    plan = single_order_plan(include_fill=False)
    path = tmp_path / "open.sqlite"
    journal = SQLiteEventJournal(path)
    try:
        SimulationRuntime(journal=journal).run(plan, through_ordinal=4)
    finally:
        journal.close()
    reopened = SQLiteEventJournal(path)
    try:
        with pytest.raises(SimulationRuntimeError, match="deferred to PF10"):
            SimulationRuntime(journal=reopened).run(plan)
    finally:
        reopened.close()


def test_degraded_safety_blocks_new_exposure(tmp_path) -> None:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    commands = [
        command(1, START + timedelta(minutes=1), SimulationCommandKind.SAFETY_STATUS, {
            "status": "DEGRADED", "reason_code": "SIM_DEGRADED", "detail": "fixture degraded"
        }),
        command(2, T0, SimulationCommandKind.OMS_CREATE, {"intent": intent.to_dict()}),
        command(3, T0 + timedelta(seconds=1), SimulationCommandKind.OMS_RISK_APPROVE, {"order_id": intent.order_id}),
        command(4, T0 + timedelta(seconds=2), SimulationCommandKind.OMS_SUBMIT, {"order_id": intent.order_id}),
    ]
    plan = SimulationPlan.create(name="reducing-block", started_at=START, ends_at=END, commands=commands)
    journal = SQLiteEventJournal(tmp_path / "reducing.sqlite")
    try:
        with pytest.raises(Exception, match="blocks simulated exposure increases"):
            SimulationRuntime(journal=journal).run(plan)
        assert any(r.event.event_type == "RUNTIME_SAFETY.TRANSITION" for r in journal.records())
    finally:
        journal.close()

def test_runtime_capabilities_explicitly_prohibit_network_live_and_deployed_paper(tmp_path) -> None:
    journal = SQLiteEventJournal(tmp_path / "caps.sqlite")
    try:
        runtime = SimulationRuntime(journal=journal)
        assert runtime.broker_kind == "SIMULATED"
        assert runtime.network_io_enabled is False
        assert runtime.live_order_submission_enabled is False
        assert runtime.deployed_paper_trading_enabled is False
    finally:
        journal.close()


def test_tampered_command_id_is_rejected() -> None:
    good = command(1, START, SimulationCommandKind.OMS_CANCEL, {"order_id": "x"})
    with pytest.raises(SimulationContractError, match="command_id"):
        SimulationCommand(good.ordinal, good.at, good.kind, good.payload, "0" * 64)


def test_second_plan_cannot_share_same_journal(tmp_path) -> None:
    first = single_order_plan()
    journal = SQLiteEventJournal(tmp_path / "one-session.sqlite")
    try:
        SimulationRuntime(journal=journal).run(first)
        lead = planned_lead(LeadDirection.SHORT)
        intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
        other = SimulationPlan.create(
            name="other",
            started_at=START,
            ends_at=END,
            commands=[command(1, T0, SimulationCommandKind.OMS_CREATE, {"intent": intent.to_dict()})],
        )
        with pytest.raises(SimulationRuntimeError, match="only one"):
            SimulationRuntime(journal=journal).run(other)
    finally:
        journal.close()


def test_explicit_recovery_allows_later_simulated_exposure(tmp_path) -> None:
    lead = planned_lead()
    intent = OrderIntent.from_trade_lead(lead, purpose=OrderPurpose.INCREASE_EXPOSURE, created_at=T0)
    commands = [
        command(1, START + timedelta(minutes=1), SimulationCommandKind.SAFETY_STATUS, {
            "status": "DEGRADED", "reason_code": "SIM_DEGRADED", "detail": "degraded"
        }),
        command(2, START + timedelta(minutes=2), SimulationCommandKind.SAFETY_STATUS, {
            "status": "HEALTHY", "reason_code": "SIM_HEALTHY", "detail": "cleared",
            "recovery_approved_by": "fixture-operator", "recovery_reason": "synthetic approval"
        }),
        command(3, T0, SimulationCommandKind.OMS_CREATE, {"intent": intent.to_dict()}),
        command(4, T0 + timedelta(seconds=1), SimulationCommandKind.OMS_RISK_APPROVE, {"order_id": intent.order_id}),
        command(5, T0 + timedelta(seconds=2), SimulationCommandKind.OMS_SUBMIT, {"order_id": intent.order_id}),
        command(6, T0 + timedelta(seconds=3), SimulationCommandKind.OMS_FILL, {
            "order_id": intent.order_id, "quantity": 3, "price": "99", "execution_id": "recovered-e1"
        }),
    ]
    plan = SimulationPlan.create(name="recovery", started_at=START, ends_at=END, commands=commands)
    journal = SQLiteEventJournal(tmp_path / "recovery.sqlite")
    try:
        result = SimulationRuntime(journal=journal).run(plan)
        assert result.status == "COMPLETED"
        assert result.runtime_state.value == "ACTIVE"
        transitions = [r.event for r in journal.records() if r.event.event_type == "RUNTIME_SAFETY.TRANSITION"]
        assert len(transitions) == 2
        assert transitions[-1].payload["trigger"] == "EXPLICIT_RECOVERY"
    finally:
        journal.close()

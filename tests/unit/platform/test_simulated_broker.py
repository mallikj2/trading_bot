from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.platform.orders import OrderIntent, OrderPurpose, OrderSide, OrderType, TimeInForce
from trading_bot.platform.simulated_broker import (
    BrokerTruthState,
    ClientCancelOutcome,
    ClientSubmissionOutcome,
    SimulatedBroker,
    SimulatedBrokerError,
    SubmissionPlan,
)

UTC = timezone.utc
T0 = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)


def intent(qty: int = 3) -> OrderIntent:
    return OrderIntent.create(
        source_lead_id="lead-x",
        source_lead_hash="a" * 64,
        instrument_id=UUID("11111111-2222-3333-4444-555555555555"),
        symbol="TEST",
        side=OrderSide.BUY,
        purpose=OrderPurpose.INCREASE_EXPOSURE,
        quantity=qty,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        created_at=T0,
        strategy_id="CSMOM-LS",
        strategy_version="v0.2",
        decision_at=T0 - timedelta(minutes=30),
    )


def test_simulated_broker_is_explicitly_network_free() -> None:
    broker = SimulatedBroker()
    assert broker.broker_kind == "SIMULATED"
    assert broker.network_io_enabled is False
    assert broker.live_order_submission_enabled is False


def test_acknowledged_submission_has_deterministic_broker_id() -> None:
    broker = SimulatedBroker()
    order = intent()
    result = broker.submit(order, submitted_at=T0)
    assert result.client_outcome == ClientSubmissionOutcome.ACKNOWLEDGED
    assert result.broker_order_id == broker.broker_order_id(order.order_id)


def test_unknown_client_outcome_can_hide_acknowledged_truth() -> None:
    broker = SimulatedBroker()
    order = intent()
    result = broker.submit(
        order,
        submitted_at=T0,
        plan=SubmissionPlan(ClientSubmissionOutcome.UNKNOWN, BrokerTruthState.ACKNOWLEDGED, "network timeout"),
    )
    assert result.client_outcome == ClientSubmissionOutcome.UNKNOWN
    snapshot = broker.reconcile(order.order_id, reconciled_at=T0 + timedelta(seconds=1))
    assert snapshot.truth == BrokerTruthState.ACKNOWLEDGED


def test_duplicate_submit_is_rejected_not_silently_duplicated() -> None:
    broker = SimulatedBroker()
    order = intent()
    broker.submit(order, submitted_at=T0)
    with pytest.raises(SimulatedBrokerError, match="duplicate submit"):
        broker.submit(order, submitted_at=T0 + timedelta(seconds=1))
    assert broker.submission_count(order.order_id) == 2


def test_partial_then_full_fill_updates_broker_truth() -> None:
    broker = SimulatedBroker()
    order = intent(3)
    broker.submit(order, submitted_at=T0)
    broker.fill(order.order_id, quantity=1, price="100", occurred_at=T0 + timedelta(seconds=1), execution_id="e1")
    assert broker.reconcile(order.order_id, reconciled_at=T0 + timedelta(seconds=2)).truth == BrokerTruthState.PARTIALLY_FILLED
    broker.fill(order.order_id, quantity=2, price="101", occurred_at=T0 + timedelta(seconds=3), execution_id="e2")
    snapshot = broker.reconcile(order.order_id, reconciled_at=T0 + timedelta(seconds=4))
    assert snapshot.truth == BrokerTruthState.FILLED
    assert sum(fill.quantity for fill in snapshot.fills) == 3


def test_broker_rejects_overfill_and_duplicate_execution() -> None:
    broker = SimulatedBroker()
    order = intent(2)
    broker.submit(order, submitted_at=T0)
    broker.fill(order.order_id, quantity=1, price="100", occurred_at=T0 + timedelta(seconds=1), execution_id="e1")
    with pytest.raises(SimulatedBrokerError, match="duplicate"):
        broker.fill(order.order_id, quantity=1, price="100", occurred_at=T0 + timedelta(seconds=2), execution_id="e1")
    with pytest.raises(SimulatedBrokerError, match="overfill"):
        broker.fill(order.order_id, quantity=2, price="100", occurred_at=T0 + timedelta(seconds=2), execution_id="e2")


def test_cancel_changes_broker_truth_and_prevents_future_fill() -> None:
    broker = SimulatedBroker()
    order = intent()
    broker.submit(order, submitted_at=T0)
    result = broker.cancel(order.order_id, canceled_at=T0 + timedelta(seconds=1), client_outcome=ClientCancelOutcome.CANCELED)
    assert result.client_outcome == ClientCancelOutcome.CANCELED
    assert broker.reconcile(order.order_id, reconciled_at=T0 + timedelta(seconds=2)).truth == BrokerTruthState.CANCELED
    with pytest.raises(SimulatedBrokerError, match="cannot fill"):
        broker.fill(order.order_id, quantity=1, price=Decimal("100"), occurred_at=T0 + timedelta(seconds=3), execution_id="e1")

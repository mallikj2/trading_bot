from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.platform.events import DomainEvent
from trading_bot.platform.orders import (
    OMSContractError,
    OMSStateError,
    OrderIntent,
    OrderProjector,
    OrderPurpose,
    OrderSide,
    OrderState,
    OrderType,
    TimeInForce,
    ensure_runtime_permission,
    order_event,
)
from trading_bot.platform.runtime_safety import RuntimeSafetyState

UTC = timezone.utc
T0 = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)
INSTRUMENT = UUID("11111111-2222-3333-4444-555555555555")
LEAD_HASH = "a" * 64


def intent(*, purpose: OrderPurpose = OrderPurpose.INCREASE_EXPOSURE, side: OrderSide = OrderSide.BUY, qty: int = 4) -> OrderIntent:
    return OrderIntent.create(
        source_lead_id="lead_test",
        source_lead_hash=LEAD_HASH,
        instrument_id=INSTRUMENT,
        symbol="TEST",
        side=side,
        purpose=purpose,
        quantity=qty,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        created_at=T0,
        strategy_id="CSMOM-LS",
        strategy_version="v0.2",
        decision_at=T0 - timedelta(minutes=30),
    )


def ev(event_type: str, order: OrderIntent, *, at: datetime, cause: str | None, payload: dict | None = None) -> DomainEvent:
    return order_event(
        event_type=event_type,
        order_id=order.order_id,
        occurred_at=at,
        correlation_id=order.order_id,
        causation_id=cause,
        payload=payload or {},
    )


def create(projector: OrderProjector, order: OrderIntent) -> DomainEvent:
    event = order_event(
        event_type="OMS.ORDER_CREATED",
        order_id=order.order_id,
        occurred_at=order.created_at,
        correlation_id=order.order_id,
        payload={"intent": order.to_dict()},
    )
    projector.apply(event)
    return event


def test_order_intent_is_deterministic_and_roundtrips() -> None:
    a = intent()
    b = intent()
    assert a.order_id == b.order_id
    assert a.content_hash == b.content_hash
    assert OrderIntent.from_dict(a.to_dict()) == a


def test_order_contract_rejects_invalid_quantity_and_limit_combinations() -> None:
    with pytest.raises(OMSContractError, match="positive integer"):
        intent(qty=0)
    with pytest.raises(OMSContractError, match="MARKET order"):
        OrderIntent.create(
            source_lead_id="lead_test",
            source_lead_hash=LEAD_HASH,
            instrument_id=INSTRUMENT,
            symbol="TEST",
            side=OrderSide.BUY,
            purpose=OrderPurpose.INCREASE_EXPOSURE,
            quantity=1,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            created_at=T0,
            strategy_id="CSMOM-LS",
            strategy_version="v0.2",
            decision_at=T0 - timedelta(minutes=1),
            limit_price="10",
        )
    with pytest.raises(OMSContractError, match="LIMIT order requires"):
        OrderIntent.create(
            source_lead_id="lead_test",
            source_lead_hash=LEAD_HASH,
            instrument_id=INSTRUMENT,
            symbol="TEST",
            side=OrderSide.BUY,
            purpose=OrderPurpose.INCREASE_EXPOSURE,
            quantity=1,
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            created_at=T0,
            strategy_id="CSMOM-LS",
            strategy_version="v0.2",
            decision_at=T0 - timedelta(minutes=1),
        )


def test_projector_happy_path_partial_then_full_fill() -> None:
    order = intent(qty=4)
    projector = OrderProjector()
    prior = create(projector, order)
    for event_type in ("OMS.ORDER_RISK_APPROVED", "OMS.ORDER_SUBMITTING", "OMS.ORDER_SUBMITTED"):
        prior = ev(event_type, order, at=T0 + timedelta(seconds=1), cause=prior.event_id)
        projector.apply(prior)
    prior = ev(
        "OMS.ORDER_ACKNOWLEDGED",
        order,
        at=T0 + timedelta(seconds=2),
        cause=prior.event_id,
        payload={"broker_order_id": "sim-x"},
    )
    projector.apply(prior)
    partial = ev(
        "OMS.ORDER_PARTIALLY_FILLED",
        order,
        at=T0 + timedelta(seconds=3),
        cause=prior.event_id,
        payload={
            "broker_order_id": "sim-x",
            "fill": {"execution_id": "e1", "quantity": 1, "price": "100", "occurred_at": (T0 + timedelta(seconds=3)).isoformat()},
        },
    )
    snap = projector.apply(partial)
    assert snap.state == OrderState.PARTIALLY_FILLED
    assert snap.filled_quantity == 1
    full = ev(
        "OMS.ORDER_FILLED",
        order,
        at=T0 + timedelta(seconds=4),
        cause=partial.event_id,
        payload={
            "broker_order_id": "sim-x",
            "fill": {"execution_id": "e2", "quantity": 3, "price": "102", "occurred_at": (T0 + timedelta(seconds=4)).isoformat()},
        },
    )
    snap = projector.apply(full)
    assert snap.state == OrderState.FILLED
    assert snap.filled_quantity == 4
    assert snap.average_fill_price == Decimal("101.5")


def test_projector_rejects_overfill_and_duplicate_execution() -> None:
    order = intent(qty=2)
    projector = OrderProjector()
    prior = create(projector, order)
    for event_type in ("OMS.ORDER_RISK_APPROVED", "OMS.ORDER_SUBMITTING", "OMS.ORDER_SUBMITTED"):
        prior = ev(event_type, order, at=T0 + timedelta(seconds=1), cause=prior.event_id)
        projector.apply(prior)
    prior = ev("OMS.ORDER_ACKNOWLEDGED", order, at=T0 + timedelta(seconds=2), cause=prior.event_id, payload={"broker_order_id": "sim-x"})
    projector.apply(prior)
    fill = ev("OMS.ORDER_PARTIALLY_FILLED", order, at=T0 + timedelta(seconds=3), cause=prior.event_id, payload={
        "broker_order_id": "sim-x",
        "fill": {"execution_id": "e1", "quantity": 1, "price": "100", "occurred_at": (T0 + timedelta(seconds=3)).isoformat()},
    })
    projector.apply(fill)
    duplicate = ev("OMS.ORDER_FILLED", order, at=T0 + timedelta(seconds=4), cause=fill.event_id, payload={
        "broker_order_id": "sim-x",
        "fill": {"execution_id": "e1", "quantity": 1, "price": "100", "occurred_at": (T0 + timedelta(seconds=4)).isoformat()},
    })
    with pytest.raises(OMSStateError, match="duplicate execution_id"):
        projector.apply(duplicate)
    over = ev("OMS.ORDER_FILLED", order, at=T0 + timedelta(seconds=4), cause=fill.event_id, payload={
        "broker_order_id": "sim-x",
        "fill": {"execution_id": "e2", "quantity": 2, "price": "100", "occurred_at": (T0 + timedelta(seconds=4)).isoformat()},
    })
    with pytest.raises(OMSStateError, match="overfill"):
        projector.apply(over)


def test_unknown_can_only_move_to_reconciling() -> None:
    order = intent()
    projector = OrderProjector()
    prior = create(projector, order)
    for event_type in ("OMS.ORDER_RISK_APPROVED", "OMS.ORDER_SUBMITTING", "OMS.ORDER_SUBMITTED"):
        prior = ev(event_type, order, at=T0 + timedelta(seconds=1), cause=prior.event_id)
        projector.apply(prior)
    unknown = ev("OMS.ORDER_UNKNOWN", order, at=T0 + timedelta(seconds=2), cause=prior.event_id, payload={"reason": "timeout", "broker_order_id": "sim-x"})
    projector.apply(unknown)
    with pytest.raises(OMSStateError, match="invalid order transition"):
        projector.apply(ev("OMS.ORDER_SUBMITTING", order, at=T0 + timedelta(seconds=3), cause=unknown.event_id))
    snap = projector.apply(ev("OMS.ORDER_RECONCILING", order, at=T0 + timedelta(seconds=3), cause=unknown.event_id))
    assert snap.state == OrderState.RECONCILING


def test_rejection_requires_reason() -> None:
    order = intent()
    projector = OrderProjector()
    prior = create(projector, order)
    rejected = ev("OMS.ORDER_REJECTED", order, at=T0 + timedelta(seconds=1), cause=prior.event_id)
    with pytest.raises(OMSContractError, match="reason"):
        projector.apply(rejected)


def test_runtime_permissions_active_reducing_halted() -> None:
    increase = intent(purpose=OrderPurpose.INCREASE_EXPOSURE, side=OrderSide.BUY)
    reduce = intent(purpose=OrderPurpose.REDUCE_EXPOSURE, side=OrderSide.SELL)
    ensure_runtime_permission(increase, RuntimeSafetyState.ACTIVE)
    ensure_runtime_permission(reduce, RuntimeSafetyState.ACTIVE)
    with pytest.raises(OMSStateError, match="blocks simulated exposure increases"):
        ensure_runtime_permission(increase, RuntimeSafetyState.REDUCING)
    ensure_runtime_permission(reduce, RuntimeSafetyState.REDUCING)
    with pytest.raises(OMSStateError, match="blocks simulated exposure"):
        ensure_runtime_permission(reduce, RuntimeSafetyState.HALTED)


def test_event_delivery_is_idempotent() -> None:
    order = intent()
    projector = OrderProjector()
    created = create(projector, order)
    first_hash = projector.state_hash
    snap = projector.apply(created)
    assert snap.state == OrderState.CREATED
    assert projector.state_hash == first_hash

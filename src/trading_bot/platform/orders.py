"""Deterministic order-management domain for Phase 02B PF06.

PF06 models order intent and broker facts without any live-broker connectivity.
All order state is reconstructed from immutable DomainEvents.  An UNKNOWN order
must be reconciled; it may never be blindly resubmitted.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping
from uuid import UUID

from trading_bot.data.time_utils import require_aware
from trading_bot.platform.events import DomainEvent, canonical_json
from trading_bot.platform.leads import LeadDirection, LeadLifecycleState, TradeLead
from trading_bot.platform.runtime_safety import RuntimeSafetyState, permissions_for


class OMSContractError(ValueError):
    """Raised when order intent, state, or broker facts violate the OMS contract."""


class OMSStateError(OMSContractError):
    """Raised on an invalid order lifecycle transition."""


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"


class OrderPurpose(str, Enum):
    INCREASE_EXPOSURE = "INCREASE_EXPOSURE"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class TimeInForce(str, Enum):
    DAY = "DAY"


class OrderState(str, Enum):
    CREATED = "CREATED"
    RISK_APPROVED = "RISK_APPROVED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"


_TERMINAL_STATES = {
    OrderState.FILLED,
    OrderState.REJECTED,
    OrderState.CANCELED,
    OrderState.EXPIRED,
}

_ALLOWED_TRANSITIONS: dict[OrderState, frozenset[OrderState]] = {
    OrderState.CREATED: frozenset({OrderState.RISK_APPROVED, OrderState.REJECTED}),
    OrderState.RISK_APPROVED: frozenset({OrderState.SUBMITTING, OrderState.REJECTED}),
    OrderState.SUBMITTING: frozenset({OrderState.SUBMITTED}),
    OrderState.SUBMITTED: frozenset(
        {
            OrderState.ACKNOWLEDGED,
            OrderState.REJECTED,
            OrderState.CANCEL_PENDING,
            OrderState.UNKNOWN,
            OrderState.EXPIRED,
        }
    ),
    OrderState.ACKNOWLEDGED: frozenset(
        {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCEL_PENDING,
            OrderState.UNKNOWN,
            OrderState.EXPIRED,
        }
    ),
    OrderState.PARTIALLY_FILLED: frozenset(
        {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCEL_PENDING,
            OrderState.UNKNOWN,
            OrderState.EXPIRED,
        }
    ),
    OrderState.CANCEL_PENDING: frozenset({OrderState.CANCELED, OrderState.UNKNOWN}),
    OrderState.UNKNOWN: frozenset({OrderState.RECONCILING}),
    OrderState.RECONCILING: frozenset(
        {
            OrderState.ACKNOWLEDGED,
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.REJECTED,
            OrderState.CANCELED,
            OrderState.EXPIRED,
        }
    ),
    OrderState.FILLED: frozenset(),
    OrderState.REJECTED: frozenset(),
    OrderState.CANCELED: frozenset(),
    OrderState.EXPIRED: frozenset(),
}

_EVENT_TO_STATE = {
    "OMS.ORDER_RISK_APPROVED": OrderState.RISK_APPROVED,
    "OMS.ORDER_SUBMITTING": OrderState.SUBMITTING,
    "OMS.ORDER_SUBMITTED": OrderState.SUBMITTED,
    "OMS.ORDER_ACKNOWLEDGED": OrderState.ACKNOWLEDGED,
    "OMS.ORDER_PARTIALLY_FILLED": OrderState.PARTIALLY_FILLED,
    "OMS.ORDER_FILLED": OrderState.FILLED,
    "OMS.ORDER_REJECTED": OrderState.REJECTED,
    "OMS.ORDER_CANCEL_PENDING": OrderState.CANCEL_PENDING,
    "OMS.ORDER_CANCELED": OrderState.CANCELED,
    "OMS.ORDER_EXPIRED": OrderState.EXPIRED,
    "OMS.ORDER_UNKNOWN": OrderState.UNKNOWN,
    "OMS.ORDER_RECONCILING": OrderState.RECONCILING,
}


def _decimal(value: Decimal | str | int, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise OMSContractError(f"{field_name} must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise OMSContractError(f"{field_name} must be numeric") from exc
    if not result.is_finite():
        raise OMSContractError(f"{field_name} must be finite")
    return result


def _hash(payload: Mapping[str, Any]) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _sha256_hex(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise OMSContractError(f"{field_name} must be lowercase SHA-256 hex")
    return normalized


@dataclass(frozen=True, slots=True)
class OrderIntent:
    order_id: str
    source_lead_id: str
    source_lead_hash: str
    instrument_id: UUID
    symbol: str
    side: OrderSide
    purpose: OrderPurpose
    quantity: int
    order_type: OrderType
    time_in_force: TimeInForce
    created_at: datetime
    strategy_id: str
    strategy_version: str
    decision_at: datetime
    limit_price: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", require_aware(self.created_at, "created_at"))
        object.__setattr__(self, "decision_at", require_aware(self.decision_at, "decision_at"))
        object.__setattr__(self, "source_lead_hash", _sha256_hex(self.source_lead_hash, "source_lead_hash"))
        if not self.source_lead_id.strip() or not self.symbol.strip():
            raise OMSContractError("source_lead_id and symbol are required")
        if not self.strategy_id.strip() or not self.strategy_version.strip():
            raise OMSContractError("strategy identity is required")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity <= 0:
            raise OMSContractError("quantity must be a positive integer")
        if self.created_at < self.decision_at:
            raise OMSContractError("order cannot be created before its source decision")
        if self.order_type == OrderType.MARKET:
            if self.limit_price is not None:
                raise OMSContractError("MARKET order cannot define limit_price")
        else:
            if self.limit_price is None:
                raise OMSContractError("LIMIT order requires limit_price")
            price = _decimal(self.limit_price, "limit_price")
            if price <= 0:
                raise OMSContractError("limit_price must be positive")
            object.__setattr__(self, "limit_price", price)
        expected = f"order_{_hash(self.identity_payload())}"
        if self.order_id != expected:
            raise OMSContractError("order_id does not match deterministic intent identity")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source_lead_id": self.source_lead_id,
            "source_lead_hash": self.source_lead_hash,
            "instrument_id": str(self.instrument_id),
            "symbol": self.symbol,
            "side": self.side.value,
            "purpose": self.purpose.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "time_in_force": self.time_in_force.value,
            "created_at": self.created_at.isoformat(),
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "decision_at": self.decision_at.isoformat(),
            "limit_price": None if self.limit_price is None else str(self.limit_price),
        }

    @property
    def content_hash(self) -> str:
        return _hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"order_id": self.order_id, **self.identity_payload()}

    @classmethod
    def create(
        cls,
        *,
        source_lead_id: str,
        source_lead_hash: str,
        instrument_id: UUID,
        symbol: str,
        side: OrderSide,
        purpose: OrderPurpose,
        quantity: int,
        order_type: OrderType,
        time_in_force: TimeInForce,
        created_at: datetime,
        strategy_id: str,
        strategy_version: str,
        decision_at: datetime,
        limit_price: Decimal | str | int | None = None,
    ) -> "OrderIntent":
        created = require_aware(created_at, "created_at")
        decision = require_aware(decision_at, "decision_at")
        normalized_limit = None if limit_price is None else _decimal(limit_price, "limit_price")
        payload = {
            "source_lead_id": source_lead_id,
            "source_lead_hash": source_lead_hash,
            "instrument_id": str(instrument_id),
            "symbol": symbol,
            "side": side.value,
            "purpose": purpose.value,
            "quantity": quantity,
            "order_type": order_type.value,
            "time_in_force": time_in_force.value,
            "created_at": created.isoformat(),
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
            "decision_at": decision.isoformat(),
            "limit_price": None if normalized_limit is None else str(normalized_limit),
        }
        return cls(order_id=f"order_{_hash(payload)}", limit_price=normalized_limit, **{
            "source_lead_id": source_lead_id,
            "source_lead_hash": source_lead_hash,
            "instrument_id": instrument_id,
            "symbol": symbol,
            "side": side,
            "purpose": purpose,
            "quantity": quantity,
            "order_type": order_type,
            "time_in_force": time_in_force,
            "created_at": created,
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
            "decision_at": decision,
        })

    @classmethod
    def from_trade_lead(
        cls,
        lead: TradeLead,
        *,
        purpose: OrderPurpose,
        created_at: datetime,
        order_type: OrderType = OrderType.MARKET,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Decimal | str | int | None = None,
    ) -> "OrderIntent":
        if lead.proposed_shares is None:
            raise OMSContractError("TradeLead requires proposed_shares before order creation")
        if purpose == OrderPurpose.INCREASE_EXPOSURE:
            if lead.state != LeadLifecycleState.PLANNED:
                raise OMSContractError("increase-exposure order requires PLANNED TradeLead")
            side = OrderSide.BUY if lead.direction == LeadDirection.LONG else OrderSide.SELL_SHORT
        else:
            if lead.state not in {LeadLifecycleState.ENTERED, LeadLifecycleState.EXIT_PENDING}:
                raise OMSContractError("reduce-exposure order requires ENTERED or EXIT_PENDING TradeLead")
            side = OrderSide.SELL if lead.direction == LeadDirection.LONG else OrderSide.BUY_TO_COVER
        return cls.create(
            source_lead_id=lead.lead_id,
            source_lead_hash=lead.content_hash,
            instrument_id=lead.instrument_id,
            symbol=lead.display_symbol,
            side=side,
            purpose=purpose,
            quantity=lead.proposed_shares,
            order_type=order_type,
            time_in_force=time_in_force,
            created_at=created_at,
            strategy_id=lead.strategy_id,
            strategy_version=lead.strategy_version,
            decision_at=lead.decision_at,
            limit_price=limit_price,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OrderIntent":
        raw_limit = payload.get("limit_price")
        return cls(
            order_id=str(payload["order_id"]),
            source_lead_id=str(payload["source_lead_id"]),
            source_lead_hash=str(payload["source_lead_hash"]),
            instrument_id=UUID(str(payload["instrument_id"])),
            symbol=str(payload["symbol"]),
            side=OrderSide(str(payload["side"])),
            purpose=OrderPurpose(str(payload["purpose"])),
            quantity=int(payload["quantity"]),
            order_type=OrderType(str(payload["order_type"])),
            time_in_force=TimeInForce(str(payload["time_in_force"])),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            strategy_id=str(payload["strategy_id"]),
            strategy_version=str(payload["strategy_version"]),
            decision_at=datetime.fromisoformat(str(payload["decision_at"])),
            limit_price=None if raw_limit is None else Decimal(str(raw_limit)),
        )


@dataclass(frozen=True, slots=True)
class Fill:
    execution_id: str
    quantity: int
    price: Decimal
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not self.execution_id.strip():
            raise OMSContractError("execution_id is required")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity <= 0:
            raise OMSContractError("fill quantity must be positive")
        price = _decimal(self.price, "fill.price")
        if price <= 0:
            raise OMSContractError("fill price must be positive")
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "occurred_at", require_aware(self.occurred_at, "fill.occurred_at"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "quantity": self.quantity,
            "price": str(self.price),
            "occurred_at": self.occurred_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Fill":
        return cls(
            execution_id=str(payload["execution_id"]),
            quantity=int(payload["quantity"]),
            price=Decimal(str(payload["price"])),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
        )


@dataclass(frozen=True, slots=True)
class OrderSnapshot:
    intent: OrderIntent
    state: OrderState
    updated_at: datetime
    broker_order_id: str | None = None
    fills: tuple[Fill, ...] = ()
    rejection_reason: str | None = None
    uncertainty_reason: str | None = None
    last_event_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "updated_at", require_aware(self.updated_at, "updated_at"))
        if self.updated_at < self.intent.created_at:
            raise OMSContractError("order snapshot cannot predate intent creation")
        execution_ids = [fill.execution_id for fill in self.fills]
        if len(execution_ids) != len(set(execution_ids)):
            raise OMSContractError("execution_id cannot be applied twice")
        if any(fill.occurred_at > self.updated_at for fill in self.fills):
            raise OMSContractError("fill cannot occur after snapshot updated_at")
        if self.filled_quantity > self.intent.quantity:
            raise OMSContractError("order cannot be overfilled")
        if self.state == OrderState.FILLED and self.filled_quantity != self.intent.quantity:
            raise OMSContractError("FILLED requires exact requested quantity")
        if self.state == OrderState.PARTIALLY_FILLED and not (0 < self.filled_quantity < self.intent.quantity):
            raise OMSContractError("PARTIALLY_FILLED requires a partial quantity")
        if self.state == OrderState.REJECTED and not self.rejection_reason:
            raise OMSContractError("REJECTED requires rejection_reason")
        if self.state == OrderState.UNKNOWN and not self.uncertainty_reason:
            raise OMSContractError("UNKNOWN requires uncertainty_reason")

    @property
    def filled_quantity(self) -> int:
        return sum(fill.quantity for fill in self.fills)

    @property
    def remaining_quantity(self) -> int:
        return self.intent.quantity - self.filled_quantity

    @property
    def average_fill_price(self) -> Decimal | None:
        if not self.fills:
            return None
        notional = sum((fill.price * fill.quantity for fill in self.fills), Decimal("0"))
        return notional / Decimal(self.filled_quantity)

    @property
    def terminal(self) -> bool:
        return self.state in _TERMINAL_STATES

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "state": self.state.value,
            "updated_at": self.updated_at.isoformat(),
            "broker_order_id": self.broker_order_id,
            "fills": [fill.to_dict() for fill in self.fills],
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "average_fill_price": None if self.average_fill_price is None else str(self.average_fill_price),
            "rejection_reason": self.rejection_reason,
            "uncertainty_reason": self.uncertainty_reason,
            "last_event_id": self.last_event_id,
        }


class OrderProjector:
    """Deterministically rebuild order state from immutable OMS events."""

    def __init__(self) -> None:
        self._orders: dict[str, OrderSnapshot] = {}
        self._event_ids: set[str] = set()

    def get(self, order_id: str) -> OrderSnapshot:
        try:
            return self._orders[order_id]
        except KeyError as exc:
            raise OMSStateError(f"unknown order {order_id}") from exc

    def snapshots(self) -> tuple[OrderSnapshot, ...]:
        return tuple(self._orders[key] for key in sorted(self._orders))

    @property
    def state_hash(self) -> str:
        payload = {snapshot.intent.order_id: snapshot.to_dict() for snapshot in self.snapshots()}
        return _hash(payload)

    def apply(self, event: DomainEvent) -> OrderSnapshot:
        if event.aggregate_type != "ORDER":
            raise OMSContractError("OrderProjector only accepts aggregate_type=ORDER")
        if event.event_id in self._event_ids:
            return self.get(event.aggregate_id)
        if event.event_type == "OMS.ORDER_CREATED":
            if event.aggregate_id in self._orders:
                raise OMSStateError("second ORDER_CREATED conflicts with existing order")
            raw_intent = event.payload.get("intent")
            if not isinstance(raw_intent, Mapping):
                raise OMSContractError("ORDER_CREATED requires intent payload")
            intent = OrderIntent.from_dict(raw_intent)
            if intent.order_id != event.aggregate_id:
                raise OMSContractError("ORDER_CREATED aggregate_id must equal order_id")
            snapshot = OrderSnapshot(
                intent=intent,
                state=OrderState.CREATED,
                updated_at=event.occurred_at,
                last_event_id=event.event_id,
            )
            self._orders[intent.order_id] = snapshot
            self._event_ids.add(event.event_id)
            return snapshot

        current = self.get(event.aggregate_id)
        if event.occurred_at < current.updated_at:
            raise OMSStateError("order events cannot move backward in time")
        target = _EVENT_TO_STATE.get(event.event_type)
        if target is None:
            raise OMSContractError(f"unsupported OMS event type {event.event_type}")
        if target not in _ALLOWED_TRANSITIONS[current.state]:
            raise OMSStateError(f"invalid order transition {current.state.value}->{target.value}")

        broker_order_id = current.broker_order_id
        raw_broker_id = event.payload.get("broker_order_id")
        if raw_broker_id is not None:
            candidate = str(raw_broker_id)
            if broker_order_id is not None and broker_order_id != candidate:
                raise OMSStateError("broker_order_id cannot change")
            broker_order_id = candidate

        fills = current.fills
        rejection_reason = current.rejection_reason
        uncertainty_reason = current.uncertainty_reason
        if target in {OrderState.PARTIALLY_FILLED, OrderState.FILLED}:
            raw_fill = event.payload.get("fill")
            if not isinstance(raw_fill, Mapping):
                raise OMSContractError(f"{target.value} requires fill payload")
            fill = Fill.from_dict(raw_fill)
            if fill.execution_id in {item.execution_id for item in fills}:
                raise OMSStateError("duplicate execution_id would double-count a fill")
            if current.filled_quantity + fill.quantity > current.intent.quantity:
                raise OMSStateError("fill would overfill order")
            fills = (*fills, fill)
            new_total = sum(item.quantity for item in fills)
            expected = OrderState.FILLED if new_total == current.intent.quantity else OrderState.PARTIALLY_FILLED
            if target != expected:
                raise OMSStateError(
                    f"fill quantity implies {expected.value}, not event state {target.value}"
                )
        if target == OrderState.REJECTED:
            rejection_reason = str(event.payload.get("reason") or "").strip()
            if not rejection_reason:
                raise OMSContractError("REJECTED requires reason")
        if target == OrderState.UNKNOWN:
            uncertainty_reason = str(event.payload.get("reason") or "").strip()
            if not uncertainty_reason:
                raise OMSContractError("UNKNOWN requires reason")
        elif target != OrderState.RECONCILING:
            uncertainty_reason = None

        snapshot = OrderSnapshot(
            intent=current.intent,
            state=target,
            updated_at=event.occurred_at,
            broker_order_id=broker_order_id,
            fills=fills,
            rejection_reason=rejection_reason,
            uncertainty_reason=uncertainty_reason,
            last_event_id=event.event_id,
        )
        self._orders[event.aggregate_id] = snapshot
        self._event_ids.add(event.event_id)
        return snapshot

    def replay(self, events: Iterable[DomainEvent]) -> "OrderProjector":
        for event in events:
            if event.aggregate_type == "ORDER":
                self.apply(event)
        return self


def ensure_runtime_permission(intent: OrderIntent, runtime_state: RuntimeSafetyState) -> None:
    permissions = permissions_for(runtime_state)
    if intent.purpose == OrderPurpose.INCREASE_EXPOSURE and not permissions.simulate_increase_exposure:
        raise OMSStateError(f"{runtime_state.value} blocks simulated exposure increases")
    if intent.purpose == OrderPurpose.REDUCE_EXPOSURE and not permissions.reduce_exposure:
        raise OMSStateError(f"{runtime_state.value} blocks simulated exposure reduction")


def order_event(
    *,
    event_type: str,
    order_id: str,
    occurred_at: datetime,
    correlation_id: str,
    payload: Mapping[str, Any],
    causation_id: str | None = None,
) -> DomainEvent:
    return DomainEvent.create(
        event_type=event_type,
        aggregate_type="ORDER",
        aggregate_id=order_id,
        occurred_at=occurred_at,
        correlation_id=correlation_id,
        causation_id=causation_id,
        producer="trading_bot.platform.oms",
        payload=payload,
    )

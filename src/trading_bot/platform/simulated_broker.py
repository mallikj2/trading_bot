"""Deterministic, network-free simulated broker and OMS service for PF06."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any

from trading_bot.data.time_utils import require_aware
from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.events import DomainEvent
from trading_bot.platform.orders import (
    Fill,
    OMSContractError,
    OMSStateError,
    OrderIntent,
    OrderProjector,
    OrderSnapshot,
    OrderState,
    ensure_runtime_permission,
    order_event,
)
from trading_bot.platform.runtime_safety import RuntimeSafetyState, permissions_for


class SimulatedBrokerError(ValueError):
    """Raised when the deterministic simulated venue contract is violated."""


class ClientSubmissionOutcome(str, Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class BrokerTruthState(str, Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class ClientCancelOutcome(str, Enum):
    CANCELED = "CANCELED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SubmissionPlan:
    client_outcome: ClientSubmissionOutcome = ClientSubmissionOutcome.ACKNOWLEDGED
    broker_truth: BrokerTruthState = BrokerTruthState.ACKNOWLEDGED
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.client_outcome == ClientSubmissionOutcome.ACKNOWLEDGED and self.broker_truth != BrokerTruthState.ACKNOWLEDGED:
            raise SimulatedBrokerError("ACKNOWLEDGED client outcome requires ACKNOWLEDGED broker truth")
        if self.client_outcome == ClientSubmissionOutcome.REJECTED and self.broker_truth != BrokerTruthState.REJECTED:
            raise SimulatedBrokerError("REJECTED client outcome requires REJECTED broker truth")
        if self.broker_truth == BrokerTruthState.REJECTED and not (self.reason or "").strip():
            raise SimulatedBrokerError("rejected submission requires reason")


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    client_outcome: ClientSubmissionOutcome
    broker_order_id: str
    reason: str | None


@dataclass(frozen=True, slots=True)
class CancelResult:
    client_outcome: ClientCancelOutcome
    broker_order_id: str


@dataclass(frozen=True, slots=True)
class ReconciliationSnapshot:
    order_id: str
    broker_order_id: str
    truth: BrokerTruthState
    fills: tuple[Fill, ...]
    rejection_reason: str | None


@dataclass(slots=True)
class _BrokerOrder:
    intent: OrderIntent
    broker_order_id: str
    truth: BrokerTruthState
    fills: list[Fill] = field(default_factory=list)
    rejection_reason: str | None = None
    submission_count: int = 1

    @property
    def filled_quantity(self) -> int:
        return sum(fill.quantity for fill in self.fills)


class SimulatedBroker:
    """Deterministic venue simulator with no network or external side effects."""

    broker_kind = "SIMULATED"
    network_io_enabled = False
    live_order_submission_enabled = False

    def __init__(self) -> None:
        self._orders: dict[str, _BrokerOrder] = {}

    @staticmethod
    def broker_order_id(order_id: str) -> str:
        return "sim_" + sha256(order_id.encode("utf-8")).hexdigest()[:24]

    def submission_count(self, order_id: str) -> int:
        return self._orders[order_id].submission_count if order_id in self._orders else 0

    @property
    def order_ids(self) -> tuple[str, ...]:
        """Stable view of simulated external order identities for reconciliation."""
        return tuple(sorted(self._orders))

    def order_intent(self, order_id: str) -> OrderIntent:
        if order_id not in self._orders:
            raise SimulatedBrokerError("simulated broker has no such order")
        return self._orders[order_id].intent

    def reconciliation_snapshots(self, *, reconciled_at: datetime) -> tuple[ReconciliationSnapshot, ...]:
        require_aware(reconciled_at, "reconciled_at")
        return tuple(self.reconcile(order_id, reconciled_at=reconciled_at) for order_id in self.order_ids)

    def position_quantities(self) -> dict[str, int]:
        """Derive simulated broker positions from execution truth only."""
        result: dict[str, int] = {}
        side_sign = {
            "BUY": 1,
            "BUY_TO_COVER": 1,
            "SELL": -1,
            "SELL_SHORT": -1,
        }
        for record in self._orders.values():
            signed = side_sign[record.intent.side.value] * record.filled_quantity
            key = str(record.intent.instrument_id)
            result[key] = result.get(key, 0) + signed
        return {key: qty for key, qty in sorted(result.items()) if qty != 0}

    def submit(
        self,
        intent: OrderIntent,
        *,
        submitted_at: datetime,
        plan: SubmissionPlan | None = None,
    ) -> SubmissionResult:
        require_aware(submitted_at, "submitted_at")
        if intent.order_id in self._orders:
            # This is intentionally strict: an UNKNOWN submission may not be
            # retried as a new submit.  Reconciliation must resolve it.
            self._orders[intent.order_id].submission_count += 1
            raise SimulatedBrokerError("duplicate submit detected; reconcile instead of resubmitting")
        plan = plan or SubmissionPlan()
        broker_id = self.broker_order_id(intent.order_id)
        record = _BrokerOrder(
            intent=intent,
            broker_order_id=broker_id,
            truth=plan.broker_truth,
            rejection_reason=plan.reason if plan.broker_truth == BrokerTruthState.REJECTED else None,
        )
        self._orders[intent.order_id] = record
        return SubmissionResult(plan.client_outcome, broker_id, plan.reason)

    def fill(
        self,
        order_id: str,
        *,
        quantity: int,
        price: Decimal | str | int,
        occurred_at: datetime,
        execution_id: str,
    ) -> Fill:
        if order_id not in self._orders:
            raise SimulatedBrokerError("cannot fill unknown simulated order")
        record = self._orders[order_id]
        if record.truth not in {BrokerTruthState.ACKNOWLEDGED, BrokerTruthState.PARTIALLY_FILLED}:
            raise SimulatedBrokerError(f"cannot fill broker order in truth state {record.truth.value}")
        if execution_id in {fill.execution_id for fill in record.fills}:
            raise SimulatedBrokerError("duplicate simulated execution_id")
        fill = Fill(execution_id, quantity, Decimal(str(price)), occurred_at)
        if record.filled_quantity + fill.quantity > record.intent.quantity:
            raise SimulatedBrokerError("simulated fill would overfill order")
        record.fills.append(fill)
        record.truth = (
            BrokerTruthState.FILLED
            if record.filled_quantity == record.intent.quantity
            else BrokerTruthState.PARTIALLY_FILLED
        )
        return fill

    def cancel(
        self,
        order_id: str,
        *,
        canceled_at: datetime,
        client_outcome: ClientCancelOutcome = ClientCancelOutcome.CANCELED,
    ) -> CancelResult:
        require_aware(canceled_at, "canceled_at")
        if order_id not in self._orders:
            raise SimulatedBrokerError("cannot cancel unknown simulated order")
        record = self._orders[order_id]
        if record.truth in {BrokerTruthState.FILLED, BrokerTruthState.REJECTED, BrokerTruthState.CANCELED, BrokerTruthState.EXPIRED}:
            raise SimulatedBrokerError(f"cannot cancel terminal broker truth {record.truth.value}")
        record.truth = BrokerTruthState.CANCELED
        return CancelResult(client_outcome, record.broker_order_id)

    def expire(self, order_id: str) -> None:
        if order_id not in self._orders:
            raise SimulatedBrokerError("cannot expire unknown simulated order")
        record = self._orders[order_id]
        if record.truth in {BrokerTruthState.FILLED, BrokerTruthState.REJECTED, BrokerTruthState.CANCELED}:
            raise SimulatedBrokerError("cannot expire terminal simulated order")
        record.truth = BrokerTruthState.EXPIRED

    def reconcile(self, order_id: str, *, reconciled_at: datetime) -> ReconciliationSnapshot:
        require_aware(reconciled_at, "reconciled_at")
        if order_id not in self._orders:
            raise SimulatedBrokerError("broker has no record of order during reconciliation")
        record = self._orders[order_id]
        return ReconciliationSnapshot(
            order_id=order_id,
            broker_order_id=record.broker_order_id,
            truth=record.truth,
            fills=tuple(record.fills),
            rejection_reason=record.rejection_reason,
        )


class OMSService:
    """Command facade that journals every OMS fact before projecting state."""

    def __init__(
        self,
        *,
        journal: SQLiteEventJournal,
        broker: SimulatedBroker,
        runtime_state: RuntimeSafetyState = RuntimeSafetyState.ACTIVE,
    ) -> None:
        self.journal = journal
        self.broker = broker
        self.runtime_state = runtime_state
        self.projector = OrderProjector()
        for record in journal.records(aggregate_type="ORDER"):
            self.projector.apply(record.event)

    def set_runtime_state(self, state: RuntimeSafetyState) -> None:
        self.runtime_state = state

    def _record(self, event: DomainEvent, *, recorded_at: datetime) -> OrderSnapshot:
        record = self.journal.append(event, recorded_at=recorded_at)
        return self.projector.apply(record.event)

    def _event(
        self,
        *,
        event_type: str,
        snapshot: OrderSnapshot,
        occurred_at: datetime,
        payload: dict[str, Any] | None = None,
    ) -> DomainEvent:
        return order_event(
            event_type=event_type,
            order_id=snapshot.intent.order_id,
            occurred_at=occurred_at,
            correlation_id=snapshot.intent.order_id,
            causation_id=snapshot.last_event_id,
            payload=payload or {},
        )

    def create(self, intent: OrderIntent, *, recorded_at: datetime | None = None) -> OrderSnapshot:
        event = order_event(
            event_type="OMS.ORDER_CREATED",
            order_id=intent.order_id,
            occurred_at=intent.created_at,
            correlation_id=intent.order_id,
            payload={"intent": intent.to_dict()},
        )
        return self._record(event, recorded_at=recorded_at or intent.created_at)

    def approve_risk(self, order_id: str, *, approved_at: datetime) -> OrderSnapshot:
        current = self.projector.get(order_id)
        if current.state != OrderState.CREATED:
            raise OMSStateError("risk approval requires CREATED order")
        return self._record(
            self._event(event_type="OMS.ORDER_RISK_APPROVED", snapshot=current, occurred_at=approved_at),
            recorded_at=approved_at,
        )

    def stage_submission(self, order_id: str, *, submitted_at: datetime) -> OrderSnapshot:
        """Persist client-side submission intent before touching broker truth.

        PF10 uses this explicit crash boundary to simulate a process disappearing
        after the venue accepted an order but before the client recorded an acknowledgement.
        """
        current = self.projector.get(order_id)
        if current.state == OrderState.UNKNOWN:
            raise OMSStateError("UNKNOWN order must reconcile; blind resubmission is prohibited")
        if current.state != OrderState.RISK_APPROVED:
            raise OMSStateError("submission requires RISK_APPROVED order")
        ensure_runtime_permission(current.intent, self.runtime_state)
        current = self._record(
            self._event(event_type="OMS.ORDER_SUBMITTING", snapshot=current, occurred_at=submitted_at),
            recorded_at=submitted_at,
        )
        return self._record(
            self._event(event_type="OMS.ORDER_SUBMITTED", snapshot=current, occurred_at=submitted_at),
            recorded_at=submitted_at,
        )

    def submit(
        self,
        order_id: str,
        *,
        submitted_at: datetime,
        plan: SubmissionPlan | None = None,
    ) -> OrderSnapshot:
        current = self.stage_submission(order_id, submitted_at=submitted_at)
        result = self.broker.submit(current.intent, submitted_at=submitted_at, plan=plan)
        if result.client_outcome == ClientSubmissionOutcome.ACKNOWLEDGED:
            event_type = "OMS.ORDER_ACKNOWLEDGED"
            payload: dict[str, Any] = {"broker_order_id": result.broker_order_id}
        elif result.client_outcome == ClientSubmissionOutcome.REJECTED:
            event_type = "OMS.ORDER_REJECTED"
            payload = {"broker_order_id": result.broker_order_id, "reason": result.reason}
        else:
            event_type = "OMS.ORDER_UNKNOWN"
            payload = {
                "broker_order_id": result.broker_order_id,
                "reason": result.reason or "submission response unavailable",
            }
        return self._record(
            self._event(event_type=event_type, snapshot=current, occurred_at=submitted_at, payload=payload),
            recorded_at=submitted_at,
        )

    def apply_fill(
        self,
        order_id: str,
        *,
        quantity: int,
        price: Decimal | str | int,
        occurred_at: datetime,
        execution_id: str,
    ) -> OrderSnapshot:
        current = self.projector.get(order_id)
        if current.state not in {OrderState.ACKNOWLEDGED, OrderState.PARTIALLY_FILLED}:
            raise OMSStateError("direct fill requires ACKNOWLEDGED/PARTIALLY_FILLED client state")
        fill = self.broker.fill(
            order_id,
            quantity=quantity,
            price=price,
            occurred_at=occurred_at,
            execution_id=execution_id,
        )
        target = "OMS.ORDER_FILLED" if current.filled_quantity + fill.quantity == current.intent.quantity else "OMS.ORDER_PARTIALLY_FILLED"
        return self._record(
            self._event(
                event_type=target,
                snapshot=current,
                occurred_at=occurred_at,
                payload={"broker_order_id": current.broker_order_id, "fill": fill.to_dict()},
            ),
            recorded_at=occurred_at,
        )

    def request_cancel(
        self,
        order_id: str,
        *,
        requested_at: datetime,
        client_outcome: ClientCancelOutcome = ClientCancelOutcome.CANCELED,
    ) -> OrderSnapshot:
        current = self.projector.get(order_id)
        if not permissions_for(self.runtime_state).cancel_open_orders:
            raise OMSStateError(f"{self.runtime_state.value} blocks cancellation")
        if current.state not in {OrderState.SUBMITTED, OrderState.ACKNOWLEDGED, OrderState.PARTIALLY_FILLED}:
            raise OMSStateError("cancel requires an open, known order state")
        current = self._record(
            self._event(event_type="OMS.ORDER_CANCEL_PENDING", snapshot=current, occurred_at=requested_at),
            recorded_at=requested_at,
        )
        result = self.broker.cancel(
            order_id,
            canceled_at=requested_at,
            client_outcome=client_outcome,
        )
        if result.client_outcome == ClientCancelOutcome.CANCELED:
            event_type = "OMS.ORDER_CANCELED"
            payload = {"broker_order_id": result.broker_order_id}
        else:
            event_type = "OMS.ORDER_UNKNOWN"
            payload = {
                "broker_order_id": result.broker_order_id,
                "reason": "cancel response unavailable",
            }
        return self._record(
            self._event(event_type=event_type, snapshot=current, occurred_at=requested_at, payload=payload),
            recorded_at=requested_at,
        )

    def expire_order(self, order_id: str, *, expired_at: datetime) -> OrderSnapshot:
        current = self.projector.get(order_id)
        if current.state not in {OrderState.SUBMITTED, OrderState.ACKNOWLEDGED, OrderState.PARTIALLY_FILLED}:
            raise OMSStateError("expiration requires an open, known order state")
        self.broker.expire(order_id)
        return self._record(
            self._event(
                event_type="OMS.ORDER_EXPIRED",
                snapshot=current,
                occurred_at=expired_at,
                payload={"broker_order_id": current.broker_order_id},
            ),
            recorded_at=expired_at,
        )

    def mark_unknown(self, order_id: str, *, observed_at: datetime, reason: str) -> OrderSnapshot:
        """Move a known open order into UNKNOWN before recovery reconciliation."""
        current = self.projector.get(order_id)
        if current.state == OrderState.UNKNOWN:
            return current
        if current.state not in {
            OrderState.SUBMITTED,
            OrderState.ACKNOWLEDGED,
            OrderState.PARTIALLY_FILLED,
            OrderState.CANCEL_PENDING,
        }:
            raise OMSStateError("only an open/nonterminal order can be marked UNKNOWN")
        detail = str(reason).strip()
        if not detail:
            raise OMSStateError("UNKNOWN transition requires reason")
        return self._record(
            self._event(
                event_type="OMS.ORDER_UNKNOWN",
                snapshot=current,
                occurred_at=observed_at,
                payload={
                    "broker_order_id": current.broker_order_id,
                    "reason": detail,
                },
            ),
            recorded_at=observed_at,
        )

    def reconcile(self, order_id: str, *, reconciled_at: datetime) -> OrderSnapshot:
        current = self.projector.get(order_id)
        if current.state != OrderState.UNKNOWN:
            raise OMSStateError("reconciliation command requires UNKNOWN order")
        current = self._record(
            self._event(event_type="OMS.ORDER_RECONCILING", snapshot=current, occurred_at=reconciled_at),
            recorded_at=reconciled_at,
        )
        broker = self.broker.reconcile(order_id, reconciled_at=reconciled_at)
        # Apply any broker fills the journal has not seen yet before resolving the
        # final state. This prevents duplicate execution accounting after restart.
        known_execution_ids = {fill.execution_id for fill in current.fills}
        for fill in broker.fills:
            if fill.execution_id in known_execution_ids:
                continue
            target = (
                "OMS.ORDER_FILLED"
                if current.filled_quantity + fill.quantity == current.intent.quantity
                else "OMS.ORDER_PARTIALLY_FILLED"
            )
            current = self._record(
                self._event(
                    event_type=target,
                    snapshot=current,
                    occurred_at=max(reconciled_at, fill.occurred_at),
                    payload={"broker_order_id": broker.broker_order_id, "fill": fill.to_dict()},
                ),
                recorded_at=max(reconciled_at, fill.occurred_at),
            )
            known_execution_ids.add(fill.execution_id)

        if current.state in {OrderState.FILLED, OrderState.PARTIALLY_FILLED} and broker.truth == BrokerTruthState.PARTIALLY_FILLED:
            return current
        if current.state == OrderState.FILLED and broker.truth == BrokerTruthState.FILLED:
            return current
        resolution = {
            BrokerTruthState.ACKNOWLEDGED: "OMS.ORDER_ACKNOWLEDGED",
            BrokerTruthState.REJECTED: "OMS.ORDER_REJECTED",
            BrokerTruthState.CANCELED: "OMS.ORDER_CANCELED",
            BrokerTruthState.EXPIRED: "OMS.ORDER_EXPIRED",
        }.get(broker.truth)
        if resolution is None:
            if broker.truth == BrokerTruthState.FILLED and current.state != OrderState.FILLED:
                raise OMSStateError("broker reports FILLED without complete execution evidence")
            if broker.truth == BrokerTruthState.PARTIALLY_FILLED and current.state != OrderState.PARTIALLY_FILLED:
                raise OMSStateError("broker reports PARTIALLY_FILLED without execution evidence")
            return current
        payload: dict[str, Any] = {"broker_order_id": broker.broker_order_id}
        if broker.truth == BrokerTruthState.REJECTED:
            payload["reason"] = broker.rejection_reason or "rejected by simulated broker"
        return self._record(
            self._event(event_type=resolution, snapshot=current, occurred_at=reconciled_at, payload=payload),
            recorded_at=reconciled_at,
        )

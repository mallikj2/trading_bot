"""Deterministic synthetic trading-session runtime for Phase 02B PF07.

The runtime deliberately uses a controlled clock and an append-only event journal.
It orchestrates existing PF01/PF03/PF04/PF06 domain services but never connects to
an external broker or provider.  Restart equivalence is supported only from a
quiescent checkpoint; recovery with open/unknown orders is explicitly deferred to
PF10.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from trading_bot.data.time_utils import require_aware
from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.events import DomainEvent, canonical_json
from trading_bot.platform.leads import TradeLead
from trading_bot.platform.orders import OrderIntent, OrderState
from trading_bot.platform.replay import ReplayEngine, TradeLeadProjector, trade_lead_snapshot_event
from trading_bot.platform.runtime_safety import (
    ProtectionEngine,
    ProtectionObservation,
    ProtectionScope,
    ProtectionStatus,
    RecoveryApproval,
    RuntimeSafetyMachine,
    RuntimeSafetyProjector,
    RuntimeSafetyState,
    StatusProtectionRule,
    protection_evaluated_event,
    runtime_safety_transition_event,
)
from trading_bot.platform.simulated_broker import (
    BrokerTruthState,
    ClientCancelOutcome,
    ClientSubmissionOutcome,
    OMSService,
    SimulatedBroker,
    SubmissionPlan,
)


class SimulationContractError(ValueError):
    """Raised when a simulation plan or command violates PF07 contracts."""


class SimulationRuntimeError(RuntimeError):
    """Raised when a deterministic session cannot continue safely."""


class RuntimeClockPort(Protocol):
    """Common clock boundary for future simulation/paper/live runtimes."""
    current_at: datetime
    def advance_to(self, value: datetime) -> "RuntimeClockPort": ...


class RuntimeBrokerPort(Protocol):
    """Capability boundary; PF07 only supplies the network-free implementation."""
    broker_kind: str
    network_io_enabled: bool
    live_order_submission_enabled: bool


class SimulationCommandKind(str, Enum):
    LEAD_SNAPSHOT = "LEAD_SNAPSHOT"
    SAFETY_STATUS = "SAFETY_STATUS"
    OMS_CREATE = "OMS_CREATE"
    OMS_RISK_APPROVE = "OMS_RISK_APPROVE"
    OMS_SUBMIT = "OMS_SUBMIT"
    OMS_FILL = "OMS_FILL"
    OMS_CANCEL = "OMS_CANCEL"
    OMS_EXPIRE = "OMS_EXPIRE"


SESSION_STARTED_EVENT = "SIMULATION.SESSION_STARTED"
CLOCK_ADVANCED_EVENT = "SIMULATION.CLOCK_ADVANCED"
COMMAND_APPLIED_EVENT = "SIMULATION.COMMAND_APPLIED"
SESSION_COMPLETED_EVENT = "SIMULATION.SESSION_COMPLETED"

_TERMINAL_ORDERS = {OrderState.FILLED, OrderState.REJECTED, OrderState.CANCELED, OrderState.EXPIRED}


def _hash(value: Mapping[str, Any]) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DeterministicClock:
    started_at: datetime
    current_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at", require_aware(self.started_at, "started_at"))
        object.__setattr__(self, "current_at", require_aware(self.current_at, "current_at"))
        object.__setattr__(self, "ends_at", require_aware(self.ends_at, "ends_at"))
        if self.current_at < self.started_at:
            raise SimulationContractError("clock current_at cannot precede started_at")
        if self.ends_at < self.current_at:
            raise SimulationContractError("clock ends_at cannot precede current_at")

    def advance_to(self, value: datetime) -> "DeterministicClock":
        target = require_aware(value, "target")
        if target < self.current_at:
            raise SimulationRuntimeError("simulation clock cannot move backward")
        if target > self.ends_at:
            raise SimulationRuntimeError("simulation command exceeds session end")
        return DeterministicClock(self.started_at, target, self.ends_at)


@dataclass(frozen=True, slots=True)
class SimulationCommand:
    ordinal: int
    at: datetime
    kind: SimulationCommandKind
    payload: Mapping[str, Any]
    command_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "at", require_aware(self.at, "at"))
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal <= 0:
            raise SimulationContractError("command ordinal must be a positive integer")
        expected = _hash(self.identity_payload())
        if self.command_id != expected:
            raise SimulationContractError("command_id does not match deterministic command content")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "at": self.at.isoformat(),
            "kind": self.kind.value,
            "payload": dict(self.payload),
        }

    @classmethod
    def create(
        cls,
        *,
        ordinal: int,
        at: datetime,
        kind: SimulationCommandKind,
        payload: Mapping[str, Any],
    ) -> "SimulationCommand":
        timestamp = require_aware(at, "at")
        body = {"ordinal": ordinal, "at": timestamp.isoformat(), "kind": kind.value, "payload": dict(payload)}
        return cls(ordinal, timestamp, kind, dict(payload), _hash(body))

    def to_dict(self) -> dict[str, Any]:
        return {"command_id": self.command_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SimulationCommand":
        payload = raw.get("payload")
        if not isinstance(payload, Mapping):
            raise SimulationContractError("simulation command payload must be an object")
        return cls(
            ordinal=int(raw["ordinal"]),
            at=datetime.fromisoformat(str(raw["at"])),
            kind=SimulationCommandKind(str(raw["kind"])),
            payload=dict(payload),
            command_id=str(raw["command_id"]),
        )


@dataclass(frozen=True, slots=True)
class SimulationPlan:
    name: str
    started_at: datetime
    ends_at: datetime
    commands: tuple[SimulationCommand, ...]
    plan_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at", require_aware(self.started_at, "started_at"))
        object.__setattr__(self, "ends_at", require_aware(self.ends_at, "ends_at"))
        if not self.name.strip():
            raise SimulationContractError("simulation plan name is required")
        if self.ends_at <= self.started_at:
            raise SimulationContractError("simulation plan must have positive duration")
        if not self.commands:
            raise SimulationContractError("simulation plan requires at least one command")
        ordinals = [command.ordinal for command in self.commands]
        if ordinals != list(range(1, len(self.commands) + 1)):
            raise SimulationContractError("command ordinals must be contiguous starting at 1")
        times = [command.at for command in self.commands]
        if times != sorted(times):
            raise SimulationContractError("simulation commands must be ordered by timestamp")
        if any(command.at < self.started_at or command.at > self.ends_at for command in self.commands):
            raise SimulationContractError("simulation command lies outside session bounds")
        if len({command.command_id for command in self.commands}) != len(self.commands):
            raise SimulationContractError("simulation command IDs must be unique")
        if self.plan_id != _hash(self.identity_payload()):
            raise SimulationContractError("plan_id does not match deterministic plan content")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "started_at": self.started_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
            "commands": [command.to_dict() for command in self.commands],
        }

    @classmethod
    def create(
        cls,
        *,
        name: str,
        started_at: datetime,
        ends_at: datetime,
        commands: Iterable[SimulationCommand],
    ) -> "SimulationPlan":
        start = require_aware(started_at, "started_at")
        end = require_aware(ends_at, "ends_at")
        materialized = tuple(commands)
        body = {
            "name": name,
            "started_at": start.isoformat(),
            "ends_at": end.isoformat(),
            "commands": [command.to_dict() for command in materialized],
        }
        return cls(name, start, end, materialized, _hash(body))

    def to_dict(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SimulationPlan":
        commands_raw = raw.get("commands")
        if not isinstance(commands_raw, list):
            raise SimulationContractError("simulation plan commands must be a list")
        return cls(
            name=str(raw["name"]),
            started_at=datetime.fromisoformat(str(raw["started_at"])),
            ends_at=datetime.fromisoformat(str(raw["ends_at"])),
            commands=tuple(SimulationCommand.from_dict(item) for item in commands_raw),
            plan_id=str(raw["plan_id"]),
        )


@dataclass(frozen=True, slots=True)
class SimulationResult:
    plan_id: str
    status: str
    applied_commands: int
    total_commands: int
    current_at: datetime
    runtime_state: RuntimeSafetyState
    lead_state_hash: str
    order_state_hash: str
    journal_head_hash: str
    journal_event_count: int
    composite_state_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "applied_commands": self.applied_commands,
            "total_commands": self.total_commands,
            "current_at": self.current_at.isoformat(),
            "runtime_state": self.runtime_state.value,
            "lead_state_hash": self.lead_state_hash,
            "order_state_hash": self.order_state_hash,
            "journal_head_hash": self.journal_head_hash,
            "journal_event_count": self.journal_event_count,
            "composite_state_hash": self.composite_state_hash,
        }


class SimulationRuntime:
    """Run one deterministic synthetic session against an append-only journal."""

    broker_kind = "SIMULATED"
    network_io_enabled = False
    live_order_submission_enabled = False
    deployed_paper_trading_enabled = False

    def __init__(self, *, journal: SQLiteEventJournal, broker: SimulatedBroker | None = None) -> None:
        self.journal = journal
        self.broker = broker or SimulatedBroker()
        self.runtime_state = self._replayed_runtime_state()
        self.oms = OMSService(journal=journal, broker=self.broker, runtime_state=self.runtime_state)

    def _replayed_runtime_state(self) -> RuntimeSafetyState:
        projector = RuntimeSafetyProjector()
        state = projector.initial_state()
        for record in self.journal.records():
            state = projector.apply(state, record.event)
        return state.state

    def _lead_hash(self) -> str:
        replay = ReplayEngine(TradeLeadProjector()).replay_records(self.journal.records())
        return replay.state_hash

    def _latest_simulation_meta(self, plan_id: str) -> DomainEvent | None:
        records = self.journal.records(correlation_id=plan_id)
        return None if not records else records[-1].event

    def _applied_command_ids(self, plan_id: str) -> set[str]:
        result: set[str] = set()
        for record in self.journal.records(correlation_id=plan_id):
            if record.event.event_type == COMMAND_APPLIED_EVENT:
                value = record.event.payload.get("command_id")
                if value is not None:
                    result.add(str(value))
        return result

    def _existing_plan_ids(self) -> set[str]:
        return {
            record.event.aggregate_id
            for record in self.journal.records(aggregate_type="SIMULATION_SESSION")
            if record.event.event_type == SESSION_STARTED_EVENT
        }

    def _current_clock(self, plan: SimulationPlan) -> DeterministicClock:
        current = plan.started_at
        for record in self.journal.records(correlation_id=plan.plan_id):
            if record.event.event_type == CLOCK_ADVANCED_EVENT:
                current = datetime.fromisoformat(str(record.event.payload["to_at"]))
        return DeterministicClock(plan.started_at, current, plan.ends_at)

    def _session_completed(self, plan_id: str) -> bool:
        return any(
            record.event.event_type == SESSION_COMPLETED_EVENT
            for record in self.journal.records(correlation_id=plan_id)
        )

    def _assert_quiescent_resume(self) -> None:
        nonterminal = [snapshot for snapshot in self.oms.projector.snapshots() if snapshot.state not in _TERMINAL_ORDERS]
        if nonterminal:
            states = ", ".join(f"{item.intent.order_id}:{item.state.value}" for item in nonterminal)
            raise SimulationRuntimeError(
                "PF07 restart requires a quiescent checkpoint; open/unknown order recovery is deferred to PF10: "
                + states
            )

    def _append_sim_event(
        self,
        *,
        plan: SimulationPlan,
        event_type: str,
        occurred_at: datetime,
        payload: Mapping[str, Any],
        causation_id: str | None,
    ) -> DomainEvent:
        event = DomainEvent.create(
            event_type=event_type,
            aggregate_type="SIMULATION_SESSION",
            aggregate_id=plan.plan_id,
            occurred_at=occurred_at,
            correlation_id=plan.plan_id,
            causation_id=causation_id,
            producer="trading_bot.platform.simulation_runtime",
            schema_version=1,
            payload=dict(payload),
        )
        return self.journal.append(event, recorded_at=occurred_at).event

    def _apply_safety_status(self, command: SimulationCommand) -> None:
        payload = command.payload
        protection_id = str(payload.get("protection_id", "SIM_RUNTIME_HEALTH"))
        scope = ProtectionScope(str(payload.get("scope", ProtectionScope.PLATFORM.value)))
        status = ProtectionStatus(str(payload["status"]))
        reason = str(payload.get("reason_code", "SIMULATION_STATUS"))
        detail = str(payload.get("detail", "synthetic runtime protection evidence"))
        evidence_hash = str(payload.get("evidence_hash") or sha256(canonical_json(dict(payload)).encode("utf-8")).hexdigest())
        expires_seconds = int(payload.get("expires_seconds", 3600))
        observation = ProtectionObservation(
            protection_id=protection_id,
            scope=scope,
            status=status,
            observed_at=command.at,
            available_at=command.at,
            expires_at=command.at + timedelta(seconds=expires_seconds),
            reason_code=reason,
            detail=detail,
            evidence_hash=evidence_hash,
        )
        evaluation = ProtectionEngine((StatusProtectionRule(protection_id, scope),)).evaluate(
            (observation,), evaluated_at=command.at
        )
        eval_event = protection_evaluated_event(evaluation)
        self.journal.append(eval_event, recorded_at=command.at)
        machine = RuntimeSafetyMachine(self.runtime_state)
        recovery: RecoveryApproval | None = None
        if evaluation.required_state.value != self.runtime_state.value and payload.get("recovery_approved_by"):
            approval_body = {
                "at": command.at.isoformat(),
                "target": evaluation.required_state.value,
                "approved_by": str(payload["recovery_approved_by"]),
                "evaluation_hash": evaluation.evaluation_hash,
            }
            recovery = RecoveryApproval(
                approval_id=_hash(approval_body),
                approved_at=command.at,
                target_state=evaluation.required_state,
                approved_by=str(payload["recovery_approved_by"]),
                reason=str(payload.get("recovery_reason", "synthetic explicit recovery approval")),
                evidence_hash=evaluation.evaluation_hash,
            )
        update = machine.apply(evaluation, recovery_approval=recovery)
        if update.transition is not None:
            transition_event = runtime_safety_transition_event(update.transition, causation_id=eval_event.event_id)
            self.journal.append(transition_event, recorded_at=update.transition.changed_at)
        elif update.recovery_required:
            raise SimulationRuntimeError("runtime recovery requires explicit recovery_approved_by")
        self.runtime_state = update.state
        self.oms.set_runtime_state(update.state)

    def _execute_command(self, command: SimulationCommand) -> None:
        payload = command.payload
        if command.kind == SimulationCommandKind.LEAD_SNAPSHOT:
            raw = payload.get("lead")
            if not isinstance(raw, Mapping):
                raise SimulationContractError("LEAD_SNAPSHOT requires lead payload")
            lead = TradeLead.from_dict(raw)
            event = trade_lead_snapshot_event(lead)
            self.journal.append(event, recorded_at=command.at)
            return
        if command.kind == SimulationCommandKind.SAFETY_STATUS:
            self._apply_safety_status(command)
            return
        if command.kind == SimulationCommandKind.OMS_CREATE:
            raw = payload.get("intent")
            if not isinstance(raw, Mapping):
                raise SimulationContractError("OMS_CREATE requires intent payload")
            self.oms.create(OrderIntent.from_dict(raw), recorded_at=command.at)
            return
        order_id = str(payload.get("order_id") or "")
        if not order_id:
            raise SimulationContractError(f"{command.kind.value} requires order_id")
        if command.kind == SimulationCommandKind.OMS_RISK_APPROVE:
            self.oms.approve_risk(order_id, approved_at=command.at)
        elif command.kind == SimulationCommandKind.OMS_SUBMIT:
            plan = SubmissionPlan(
                ClientSubmissionOutcome(str(payload.get("client_outcome", "ACKNOWLEDGED"))),
                BrokerTruthState(str(payload.get("broker_truth", "ACKNOWLEDGED"))),
                None if payload.get("reason") is None else str(payload["reason"]),
            )
            self.oms.submit(order_id, submitted_at=command.at, plan=plan)
        elif command.kind == SimulationCommandKind.OMS_FILL:
            self.oms.apply_fill(
                order_id,
                quantity=int(payload["quantity"]),
                price=str(payload["price"]),
                occurred_at=command.at,
                execution_id=str(payload["execution_id"]),
            )
        elif command.kind == SimulationCommandKind.OMS_CANCEL:
            self.oms.request_cancel(
                order_id,
                requested_at=command.at,
                client_outcome=ClientCancelOutcome(str(payload.get("client_outcome", "CANCELED"))),
            )
        elif command.kind == SimulationCommandKind.OMS_EXPIRE:
            self.oms.expire_order(order_id, expired_at=command.at)
        else:  # pragma: no cover - enum exhaustiveness guard
            raise SimulationContractError(f"unsupported simulation command {command.kind.value}")

    def run(self, plan: SimulationPlan, *, through_ordinal: int | None = None) -> SimulationResult:
        existing = self._existing_plan_ids()
        if existing and existing != {plan.plan_id}:
            raise SimulationRuntimeError("one journal may contain only one PF07 simulation session")
        already_started = plan.plan_id in existing
        if already_started and not self._session_completed(plan.plan_id):
            self._assert_quiescent_resume()
        if self._session_completed(plan.plan_id):
            return self.result(plan)

        last_meta = self._latest_simulation_meta(plan.plan_id)
        if not already_started:
            last_meta = self._append_sim_event(
                plan=plan,
                event_type=SESSION_STARTED_EVENT,
                occurred_at=plan.started_at,
                payload={"name": plan.name, "plan_hash": plan.plan_id, "command_count": len(plan.commands)},
                causation_id=None,
            )
        clock = self._current_clock(plan)
        applied = self._applied_command_ids(plan.plan_id)
        limit = len(plan.commands) if through_ordinal is None else through_ordinal
        if limit <= 0 or limit > len(plan.commands):
            raise SimulationContractError("through_ordinal must be within the simulation command range")

        for command in plan.commands:
            if command.ordinal > limit or command.command_id in applied:
                continue
            prior_at = clock.current_at
            clock = clock.advance_to(command.at)
            if clock.current_at != prior_at:
                last_meta = self._append_sim_event(
                    plan=plan,
                    event_type=CLOCK_ADVANCED_EVENT,
                    occurred_at=clock.current_at,
                    payload={"from_at": prior_at.isoformat(), "to_at": clock.current_at.isoformat()},
                    causation_id=None if last_meta is None else last_meta.event_id,
                )
            self._execute_command(command)
            last_meta = self._append_sim_event(
                plan=plan,
                event_type=COMMAND_APPLIED_EVENT,
                occurred_at=command.at,
                payload={"command_id": command.command_id, "ordinal": command.ordinal, "kind": command.kind.value},
                causation_id=None if last_meta is None else last_meta.event_id,
            )
            applied.add(command.command_id)

        if len(applied) == len(plan.commands) and all(
            snapshot.state in _TERMINAL_ORDERS for snapshot in self.oms.projector.snapshots()
        ):
            if clock.current_at < plan.ends_at:
                prior_at = clock.current_at
                clock = clock.advance_to(plan.ends_at)
                last_meta = self._append_sim_event(
                    plan=plan,
                    event_type=CLOCK_ADVANCED_EVENT,
                    occurred_at=clock.current_at,
                    payload={"from_at": prior_at.isoformat(), "to_at": clock.current_at.isoformat()},
                    causation_id=None if last_meta is None else last_meta.event_id,
                )
            self._append_sim_event(
                plan=plan,
                event_type=SESSION_COMPLETED_EVENT,
                occurred_at=clock.current_at,
                payload={"plan_hash": plan.plan_id, "applied_commands": len(applied)},
                causation_id=None if last_meta is None else last_meta.event_id,
            )
        self.journal.verify_integrity()
        return self.result(plan)

    def result(self, plan: SimulationPlan) -> SimulationResult:
        applied = self._applied_command_ids(plan.plan_id)
        status = "COMPLETED" if self._session_completed(plan.plan_id) else "IN_PROGRESS"
        clock = self._current_clock(plan)
        head = self.journal.verify_integrity()
        lead_hash = self._lead_hash()
        order_hash = self.oms.projector.state_hash
        event_count = len(self.journal.records())
        body = {
            "plan_id": plan.plan_id,
            "status": status,
            "current_at": clock.current_at.isoformat(),
            "runtime_state": self.runtime_state.value,
            "lead_state_hash": lead_hash,
            "order_state_hash": order_hash,
            "journal_head_hash": head,
            "journal_event_count": event_count,
            "applied_commands": len(applied),
            "total_commands": len(plan.commands),
        }
        return SimulationResult(
            plan_id=plan.plan_id,
            status=status,
            applied_commands=len(applied),
            total_commands=len(plan.commands),
            current_at=clock.current_at,
            runtime_state=self.runtime_state,
            lead_state_hash=lead_hash,
            order_state_hash=order_hash,
            journal_head_hash=head,
            journal_event_count=event_count,
            composite_state_hash=_hash(body),
        )


def load_plan(path: str | Path) -> SimulationPlan:
    import json

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise SimulationContractError("simulation plan JSON must contain an object")
    return SimulationPlan.from_dict(raw)

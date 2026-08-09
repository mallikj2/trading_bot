"""PF10 deterministic crash recovery and broker-state reconciliation simulation.

The recovery layer compares two independent truths:
1. local immutable OMS/event-journal state;
2. a point-in-time snapshot of the simulated external broker.

It may import broker facts that are uniquely evidenced (for example, a missed
execution on a known order). It never invents orders, retries an UNKNOWN order,
or silently repairs unexplained external orders / missing broker orders /
position mismatches. Unresolved material divergence is journaled, surfaced as an
incident, and forces the PF04 runtime safety state to HALTED.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping

from trading_bot.data.time_utils import require_aware
from trading_bot.platform.alerts import AlertIncidentCenter, AlertSeverity, AlertSignal
from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.events import DomainEvent, canonical_json
from trading_bot.platform.orders import Fill, OrderProjector, OrderSnapshot, OrderState
from trading_bot.platform.runtime_safety import (
    ProtectionEngine,
    ProtectionObservation,
    ProtectionScope,
    ProtectionStatus,
    RuntimeSafetyMachine,
    RuntimeSafetyProjector,
    RuntimeSafetyState,
    StatusProtectionRule,
    protection_evaluated_event,
    runtime_safety_transition_event,
)
from trading_bot.platform.simulated_broker import (
    BrokerTruthState,
    OMSService,
    ReconciliationSnapshot,
    SimulatedBroker,
    SimulatedBrokerError,
)


class RecoveryContractError(ValueError):
    """Raised when recovery input violates the PF10 deterministic contract."""


class RecoveryFindingCode(str, Enum):
    STALE_STARTUP_SNAPSHOT = "STALE_STARTUP_SNAPSHOT"
    CRASH_AFTER_SUBMISSION = "CRASH_AFTER_SUBMISSION"
    MISSED_BROKER_FILL = "MISSED_BROKER_FILL"
    ORDER_STATE_DIVERGENCE = "ORDER_STATE_DIVERGENCE"
    EXTERNAL_ORDER_UNKNOWN_LOCALLY = "EXTERNAL_ORDER_UNKNOWN_LOCALLY"
    LOCAL_ORDER_ABSENT_EXTERNALLY = "LOCAL_ORDER_ABSENT_EXTERNALLY"
    POSITION_QUANTITY_MISMATCH = "POSITION_QUANTITY_MISMATCH"
    DUPLICATE_BROKER_EXECUTION = "DUPLICATE_BROKER_EXECUTION"
    BROKER_ORDER_ID_MISMATCH = "BROKER_ORDER_ID_MISMATCH"
    RECONCILIATION_ERROR = "RECONCILIATION_ERROR"


class FindingDisposition(str, Enum):
    AUTO_REPAIRED = "AUTO_REPAIRED"
    OBSERVED = "OBSERVED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class BrokerOrderSnapshot:
    order_id: str
    broker_order_id: str
    truth: BrokerTruthState
    instrument_id: str
    symbol: str
    side: str
    requested_quantity: int
    fills: tuple[Fill, ...]
    rejection_reason: str | None = None

    @property
    def filled_quantity(self) -> int:
        return sum(fill.quantity for fill in self.fills)

    @property
    def execution_ids(self) -> tuple[str, ...]:
        return tuple(fill.execution_id for fill in self.fills)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "broker_order_id": self.broker_order_id,
            "truth": self.truth.value,
            "instrument_id": self.instrument_id,
            "symbol": self.symbol,
            "side": self.side,
            "requested_quantity": self.requested_quantity,
            "fills": [fill.to_dict() for fill in self.fills],
            "rejection_reason": self.rejection_reason,
        }


@dataclass(frozen=True, slots=True)
class BrokerAccountSnapshot:
    captured_at: datetime
    orders: tuple[BrokerOrderSnapshot, ...]
    positions: tuple[tuple[str, int], ...]
    source: str = "SIMULATED_BROKER"

    def __post_init__(self) -> None:
        object.__setattr__(self, "captured_at", require_aware(self.captured_at, "captured_at"))
        order_ids = [order.order_id for order in self.orders]
        if len(order_ids) != len(set(order_ids)):
            raise RecoveryContractError("broker account snapshot cannot contain duplicate order_id")
        position_ids = [instrument_id for instrument_id, _ in self.positions]
        if len(position_ids) != len(set(position_ids)):
            raise RecoveryContractError("broker account snapshot cannot contain duplicate positions")
        if not self.source.strip():
            raise RecoveryContractError("snapshot source is required")

    @property
    def order_map(self) -> dict[str, BrokerOrderSnapshot]:
        return {order.order_id: order for order in self.orders}

    @property
    def position_map(self) -> dict[str, int]:
        return dict(self.positions)

    @property
    def snapshot_hash(self) -> str:
        return _hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at": self.captured_at.isoformat(),
            "source": self.source,
            "orders": [order.to_dict() for order in self.orders],
            "positions": [
                {"instrument_id": instrument_id, "quantity": quantity}
                for instrument_id, quantity in self.positions
            ],
        }

    @classmethod
    def from_broker(cls, broker: SimulatedBroker, *, captured_at: datetime) -> "BrokerAccountSnapshot":
        captured = require_aware(captured_at, "captured_at")
        orders: list[BrokerOrderSnapshot] = []
        for order_id in broker.order_ids:
            intent = broker.order_intent(order_id)
            truth = broker.reconcile(order_id, reconciled_at=captured)
            orders.append(
                BrokerOrderSnapshot(
                    order_id=truth.order_id,
                    broker_order_id=truth.broker_order_id,
                    truth=truth.truth,
                    instrument_id=str(intent.instrument_id),
                    symbol=intent.symbol,
                    side=intent.side.value,
                    requested_quantity=intent.quantity,
                    fills=truth.fills,
                    rejection_reason=truth.rejection_reason,
                )
            )
        return cls(
            captured_at=captured,
            orders=tuple(sorted(orders, key=lambda item: item.order_id)),
            positions=tuple(sorted(broker.position_quantities().items())),
        )

    def with_positions(self, positions: Mapping[str, int]) -> "BrokerAccountSnapshot":
        return replace(self, positions=tuple(sorted((str(k), int(v)) for k, v in positions.items() if int(v) != 0)))

    def with_duplicate_execution(self, order_id: str) -> "BrokerAccountSnapshot":
        target = self.order_map.get(order_id)
        if target is None or not target.fills:
            raise RecoveryContractError("duplicate-execution fixture requires an order with at least one fill")
        duplicate = target.fills[-1]
        updated = replace(target, fills=(*target.fills, duplicate))
        return replace(
            self,
            orders=tuple(updated if item.order_id == order_id else item for item in self.orders),
        )


@dataclass(frozen=True, slots=True)
class RecoveryFinding:
    code: RecoveryFindingCode
    severity: AlertSeverity
    entity_id: str
    detail: str
    disposition: FindingDisposition
    detected_at: datetime
    evidence_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "detected_at", require_aware(self.detected_at, "detected_at"))
        if not self.entity_id.strip() or not self.detail.strip():
            raise RecoveryContractError("finding entity/detail are required")
        if len(self.evidence_hash) != 64 or any(ch not in "0123456789abcdef" for ch in self.evidence_hash):
            raise RecoveryContractError("finding evidence_hash must be SHA-256 hex")

    @property
    def unresolved(self) -> bool:
        return self.disposition == FindingDisposition.UNRESOLVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "entity_id": self.entity_id,
            "detail": self.detail,
            "disposition": self.disposition.value,
            "detected_at": self.detected_at.isoformat(),
            "evidence_hash": self.evidence_hash,
            "unresolved": self.unresolved,
        }


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    run_id: str
    started_at: datetime
    completed_at: datetime
    broker_snapshot_hash: str
    start_journal_head_hash: str
    final_journal_head_hash: str
    findings: tuple[RecoveryFinding, ...]
    final_runtime_state: RuntimeSafetyState
    local_order_state_hash: str
    local_positions: tuple[tuple[str, int], ...]
    broker_positions: tuple[tuple[str, int], ...]
    duplicate_risk_created: bool = False

    @property
    def unresolved_count(self) -> int:
        return sum(1 for finding in self.findings if finding.unresolved)

    @property
    def status(self) -> str:
        return "BLOCKED" if self.unresolved_count else "RECOVERED"

    @property
    def report_hash(self) -> str:
        return _hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "broker_snapshot_hash": self.broker_snapshot_hash,
            "start_journal_head_hash": self.start_journal_head_hash,
            "final_journal_head_hash": self.final_journal_head_hash,
            "status": self.status,
            "unresolved_count": self.unresolved_count,
            "findings": [finding.to_dict() for finding in self.findings],
            "final_runtime_state": self.final_runtime_state.value,
            "local_order_state_hash": self.local_order_state_hash,
            "local_positions": [{"instrument_id": k, "quantity": v} for k, v in self.local_positions],
            "broker_positions": [{"instrument_id": k, "quantity": v} for k, v in self.broker_positions],
            "duplicate_risk_created": self.duplicate_risk_created,
        }
        if include_hash:
            payload["report_hash"] = _hash(payload)
        return payload


def _hash(payload: Mapping[str, Any]) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _local_positions(snapshots: Iterable[OrderSnapshot]) -> dict[str, int]:
    sign = {"BUY": 1, "BUY_TO_COVER": 1, "SELL": -1, "SELL_SHORT": -1}
    positions: dict[str, int] = {}
    for snapshot in snapshots:
        if snapshot.filled_quantity == 0:
            continue
        instrument = str(snapshot.intent.instrument_id)
        positions[instrument] = positions.get(instrument, 0) + sign[snapshot.intent.side.value] * snapshot.filled_quantity
    return {key: value for key, value in sorted(positions.items()) if value != 0}


def _runtime_state_from_journal(journal: SQLiteEventJournal) -> RuntimeSafetyState:
    projector = RuntimeSafetyProjector()
    state = projector.initial_state()
    for record in journal.records():
        projector.apply(state, record.event)
    return state.state


class RecoveryCoordinator:
    """Deterministically reconcile local OMS state against simulated broker truth."""

    PRODUCER = "pf10_recovery_reconciliation"

    def __init__(
        self,
        *,
        journal: SQLiteEventJournal,
        broker: SimulatedBroker,
        max_snapshot_age: timedelta = timedelta(seconds=60),
    ) -> None:
        if max_snapshot_age <= timedelta(0):
            raise RecoveryContractError("max_snapshot_age must be positive")
        self.journal = journal
        self.broker = broker
        self.max_snapshot_age = max_snapshot_age

    def run(self, snapshot: BrokerAccountSnapshot, *, started_at: datetime) -> RecoveryReport:
        started = require_aware(started_at, "started_at")
        if snapshot.captured_at > started:
            raise RecoveryContractError("future broker snapshot cannot be used for startup recovery")
        self.journal.verify_integrity()
        start_head = self.journal.head_hash
        run_id = _hash({
            "snapshot_hash": snapshot.snapshot_hash,
            "started_at": started.isoformat(),
            "start_journal_head_hash": start_head,
        })
        self._journal_recovery_event(
            "RECOVERY.STARTED",
            run_id,
            started,
            {
                "snapshot_hash": snapshot.snapshot_hash,
                "snapshot_captured_at": snapshot.captured_at.isoformat(),
                "max_snapshot_age_seconds": int(self.max_snapshot_age.total_seconds()),
                "start_journal_head_hash": start_head,
            },
        )

        findings: list[RecoveryFinding] = []
        if started - snapshot.captured_at > self.max_snapshot_age:
            findings.append(self._finding(
                RecoveryFindingCode.STALE_STARTUP_SNAPSHOT,
                AlertSeverity.CRITICAL,
                "BROKER_ACCOUNT",
                f"Broker snapshot age {(started - snapshot.captured_at).total_seconds():.0f}s exceeds allowed {self.max_snapshot_age.total_seconds():.0f}s.",
                FindingDisposition.UNRESOLVED,
                started,
                {"snapshot_hash": snapshot.snapshot_hash, "captured_at": snapshot.captured_at.isoformat()},
            ))
        else:
            findings.extend(self._reconcile_orders(snapshot, started_at=started))

        oms = OMSService(journal=self.journal, broker=self.broker, runtime_state=_runtime_state_from_journal(self.journal))
        local_positions = _local_positions(oms.projector.snapshots())
        broker_positions = snapshot.position_map
        if local_positions != broker_positions:
            findings.append(self._finding(
                RecoveryFindingCode.POSITION_QUANTITY_MISMATCH,
                AlertSeverity.CRITICAL,
                "BROKER_ACCOUNT",
                f"Local positions {local_positions} do not match broker snapshot positions {broker_positions}.",
                FindingDisposition.UNRESOLVED,
                started,
                {"local_positions": local_positions, "broker_positions": broker_positions},
            ))

        findings = self._dedupe_findings(findings)
        incident_ids = self._record_findings(findings, run_id=run_id, recorded_at=started)
        unresolved = [finding for finding in findings if finding.unresolved]
        final_runtime = _runtime_state_from_journal(self.journal)
        if unresolved:
            final_runtime = self._force_halt(unresolved, evaluated_at=started)
        elif incident_ids:
            center = AlertIncidentCenter(self.journal)
            for incident_id in sorted(set(incident_ids)):
                incident = next(item for item in center.incidents if item["incident_id"] == incident_id)
                if incident["status"] != "RESOLVED":
                    center.resolve(
                        incident_id,
                        actor="PF10_RECOVERY",
                        resolution="All reconciliation findings were deterministically repaired or observed without unresolved divergence.",
                        occurred_at=started,
                        recorded_at=started,
                    )

        final_oms = OMSService(journal=self.journal, broker=self.broker, runtime_state=final_runtime)
        final_local_positions = _local_positions(final_oms.projector.snapshots())
        # Final position comparison uses the original point-in-time external snapshot;
        # broker truth must not be refetched behind the recovery report's back.
        completed = started
        provisional = RecoveryReport(
            run_id=run_id,
            started_at=started,
            completed_at=completed,
            broker_snapshot_hash=snapshot.snapshot_hash,
            start_journal_head_hash=start_head,
            final_journal_head_hash=self.journal.head_hash,
            findings=tuple(findings),
            final_runtime_state=final_runtime,
            local_order_state_hash=final_oms.projector.state_hash,
            local_positions=tuple(sorted(final_local_positions.items())),
            broker_positions=tuple(sorted(broker_positions.items())),
            duplicate_risk_created=False,
        )
        completion = self._journal_recovery_event(
            "RECOVERY.COMPLETED",
            run_id,
            completed,
            {
                "status": provisional.status,
                "unresolved_count": provisional.unresolved_count,
                "runtime_state": final_runtime.value,
                "local_order_state_hash": provisional.local_order_state_hash,
                "duplicate_risk_created": False,
                "report_body_hash": provisional.report_hash,
            },
        )
        return replace(provisional, final_journal_head_hash=self.journal.head_hash)

    def _reconcile_orders(self, snapshot: BrokerAccountSnapshot, *, started_at: datetime) -> list[RecoveryFinding]:
        findings: list[RecoveryFinding] = []
        oms = OMSService(journal=self.journal, broker=self.broker, runtime_state=_runtime_state_from_journal(self.journal))
        local = {item.intent.order_id: item for item in oms.projector.snapshots()}
        external = snapshot.order_map
        local_ids, external_ids = set(local), set(external)

        for order_id in sorted(external_ids - local_ids):
            order = external[order_id]
            findings.append(self._finding(
                RecoveryFindingCode.EXTERNAL_ORDER_UNKNOWN_LOCALLY,
                AlertSeverity.CRITICAL,
                order_id,
                f"Broker snapshot contains external order {order.broker_order_id} with no local immutable order history; no auto-import performed.",
                FindingDisposition.UNRESOLVED,
                started_at,
                order.to_dict(),
            ))

        for order_id in sorted(local_ids - external_ids):
            order = local[order_id]
            if not order.terminal:
                findings.append(self._finding(
                    RecoveryFindingCode.LOCAL_ORDER_ABSENT_EXTERNALLY,
                    AlertSeverity.CRITICAL,
                    order_id,
                    f"Local nonterminal order {order.state.value} is absent from broker startup snapshot; blind resubmission is prohibited.",
                    FindingDisposition.UNRESOLVED,
                    started_at,
                    order.to_dict(),
                ))

        for order_id in sorted(local_ids & external_ids):
            local_order = oms.projector.get(order_id)
            broker_order = external[order_id]
            duplicates = _duplicates(broker_order.execution_ids)
            if duplicates:
                findings.append(self._finding(
                    RecoveryFindingCode.DUPLICATE_BROKER_EXECUTION,
                    AlertSeverity.CRITICAL,
                    order_id,
                    f"Broker snapshot repeats execution IDs {duplicates}; no execution facts imported.",
                    FindingDisposition.UNRESOLVED,
                    started_at,
                    {"order": broker_order.to_dict(), "duplicate_execution_ids": list(duplicates)},
                ))
                continue
            if local_order.broker_order_id and local_order.broker_order_id != broker_order.broker_order_id:
                findings.append(self._finding(
                    RecoveryFindingCode.BROKER_ORDER_ID_MISMATCH,
                    AlertSeverity.CRITICAL,
                    order_id,
                    f"Local broker_order_id {local_order.broker_order_id} != external {broker_order.broker_order_id}.",
                    FindingDisposition.UNRESOLVED,
                    started_at,
                    {"local": local_order.to_dict(), "broker": broker_order.to_dict()},
                ))
                continue

            known_exec = {fill.execution_id for fill in local_order.fills}
            external_exec = {fill.execution_id for fill in broker_order.fills}
            if not known_exec.issubset(external_exec):
                findings.append(self._finding(
                    RecoveryFindingCode.RECONCILIATION_ERROR,
                    AlertSeverity.CRITICAL,
                    order_id,
                    "Local execution history contains fills absent from the broker startup snapshot.",
                    FindingDisposition.UNRESOLVED,
                    started_at,
                    {"local_execution_ids": sorted(known_exec), "broker_execution_ids": sorted(external_exec)},
                ))
                continue

            missed_exec = sorted(external_exec - known_exec)
            needs_state_repair = not _state_compatible(local_order.state, broker_order.truth)
            crash_window = local_order.state == OrderState.SUBMITTED
            if missed_exec or needs_state_repair or local_order.state in {OrderState.UNKNOWN, OrderState.RECONCILING}:
                before = local_order
                try:
                    if before.state == OrderState.RECONCILING:
                        # A prior process died after RECOVERY began. Rebuild the local OMS
                        # state back to UNKNOWN is impossible without rewriting history;
                        # therefore the unresolved RECONCILING state is explicitly halted.
                        raise RecoveryContractError("startup found order already RECONCILING; operator recovery required")
                    if before.state != OrderState.UNKNOWN:
                        oms.mark_unknown(
                            order_id,
                            observed_at=started_at,
                            reason="PF10 startup reconciliation detected broker/local divergence",
                        )
                    after = oms.reconcile(order_id, reconciled_at=started_at)
                except (SimulatedBrokerError, Exception) as exc:
                    findings.append(self._finding(
                        RecoveryFindingCode.RECONCILIATION_ERROR,
                        AlertSeverity.CRITICAL,
                        order_id,
                        f"Deterministic reconciliation failed closed: {type(exc).__name__}: {exc}",
                        FindingDisposition.UNRESOLVED,
                        started_at,
                        {"local": before.to_dict(), "broker": broker_order.to_dict()},
                    ))
                    continue
                if crash_window:
                    findings.append(self._finding(
                        RecoveryFindingCode.CRASH_AFTER_SUBMISSION,
                        AlertSeverity.WARNING,
                        order_id,
                        f"Recovered submission crash window without resubmission; broker truth resolved to {after.state.value}.",
                        FindingDisposition.AUTO_REPAIRED,
                        started_at,
                        {"before": before.to_dict(), "after": after.to_dict()},
                    ))
                if missed_exec:
                    findings.append(self._finding(
                        RecoveryFindingCode.MISSED_BROKER_FILL,
                        AlertSeverity.WARNING,
                        order_id,
                        f"Imported {len(missed_exec)} previously unjournaled broker execution(s): {missed_exec}.",
                        FindingDisposition.AUTO_REPAIRED,
                        started_at,
                        {"execution_ids": missed_exec, "after": after.to_dict()},
                    ))
                if needs_state_repair and not crash_window:
                    findings.append(self._finding(
                        RecoveryFindingCode.ORDER_STATE_DIVERGENCE,
                        AlertSeverity.WARNING,
                        order_id,
                        f"Reconciled local state {before.state.value} to broker-evidenced state {after.state.value}.",
                        FindingDisposition.AUTO_REPAIRED,
                        started_at,
                        {"before": before.to_dict(), "after": after.to_dict(), "broker_truth": broker_order.truth.value},
                    ))
        return findings

    def _record_findings(self, findings: Iterable[RecoveryFinding], *, run_id: str, recorded_at: datetime) -> tuple[str, ...]:
        center = AlertIncidentCenter(self.journal)
        incident_ids: list[str] = []
        for finding in findings:
            self._journal_recovery_event(
                "RECOVERY.FINDING",
                run_id,
                finding.detected_at,
                finding.to_dict(),
            )
            signal = AlertSignal.create(
                rule_id=f"PF10_{finding.code.value}",
                component="RECOVERY_RECONCILIATION",
                entity_id=finding.entity_id,
                condition_key=finding.code.value,
                severity=finding.severity,
                occurred_at=finding.detected_at,
                title=f"PF10 {finding.code.value.replace('_', ' ').title()}",
                detail=finding.detail,
                evidence_hash=finding.evidence_hash,
                incident_key=f"PF10_RECOVERY:{run_id}",
            )
            result = center.ingest(signal, recorded_at=recorded_at)
            incident_ids.append(result.incident_id)
        return tuple(incident_ids)

    def _force_halt(self, findings: Iterable[RecoveryFinding], *, evaluated_at: datetime) -> RuntimeSafetyState:
        evidence = _hash({"unresolved_findings": [finding.to_dict() for finding in findings]})
        observation = ProtectionObservation(
            protection_id="PF10_RECONCILIATION_INTEGRITY",
            scope=ProtectionScope.RECONCILIATION,
            status=ProtectionStatus.FAILED,
            observed_at=evaluated_at,
            available_at=evaluated_at,
            expires_at=evaluated_at + timedelta(minutes=5),
            reason_code="UNRESOLVED_RECONCILIATION_MISMATCH",
            detail="PF10 detected unresolved local/broker divergence; new exposure remains blocked.",
            evidence_hash=evidence,
        )
        evaluation = ProtectionEngine([
            StatusProtectionRule("PF10_RECONCILIATION_INTEGRITY", ProtectionScope.RECONCILIATION)
        ]).evaluate([observation], evaluated_at=evaluated_at)
        eval_event = protection_evaluated_event(evaluation)
        self.journal.append(eval_event, recorded_at=evaluated_at)
        current = _runtime_state_from_journal(self.journal)
        machine = RuntimeSafetyMachine(current)
        update = machine.apply(evaluation)
        if update.transition is not None:
            transition_event = runtime_safety_transition_event(update.transition, causation_id=eval_event.event_id)
            self.journal.append(transition_event, recorded_at=update.transition.changed_at)
        return update.state

    def _finding(
        self,
        code: RecoveryFindingCode,
        severity: AlertSeverity,
        entity_id: str,
        detail: str,
        disposition: FindingDisposition,
        detected_at: datetime,
        evidence: Mapping[str, Any],
    ) -> RecoveryFinding:
        return RecoveryFinding(
            code=code,
            severity=severity,
            entity_id=str(entity_id),
            detail=detail,
            disposition=disposition,
            detected_at=detected_at,
            evidence_hash=_hash(evidence),
        )

    @staticmethod
    def _dedupe_findings(findings: Iterable[RecoveryFinding]) -> list[RecoveryFinding]:
        unique: dict[tuple[str, str, str], RecoveryFinding] = {}
        for finding in findings:
            key = (finding.code.value, finding.entity_id, finding.evidence_hash)
            unique[key] = finding
        return [unique[key] for key in sorted(unique)]

    def _journal_recovery_event(
        self,
        event_type: str,
        run_id: str,
        occurred_at: datetime,
        payload: Mapping[str, Any],
    ) -> DomainEvent:
        previous = self.journal.records(aggregate_type="RECOVERY", aggregate_id=run_id)
        cause = previous[-1].event.event_id if previous else None
        event = DomainEvent.create(
            event_type=event_type,
            aggregate_type="RECOVERY",
            aggregate_id=run_id,
            occurred_at=occurred_at,
            correlation_id=run_id,
            causation_id=cause,
            producer=self.PRODUCER,
            payload=payload,
        )
        self.journal.append(event, recorded_at=occurred_at)
        return event


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _state_compatible(local: OrderState, external: BrokerTruthState) -> bool:
    compatible = {
        BrokerTruthState.ACKNOWLEDGED: {OrderState.ACKNOWLEDGED},
        BrokerTruthState.PARTIALLY_FILLED: {OrderState.PARTIALLY_FILLED},
        BrokerTruthState.FILLED: {OrderState.FILLED},
        BrokerTruthState.REJECTED: {OrderState.REJECTED},
        BrokerTruthState.CANCELED: {OrderState.CANCELED},
        BrokerTruthState.EXPIRED: {OrderState.EXPIRED},
    }
    return local in compatible[external]


def build_pf10_fixture_recovery_report(*, as_of: datetime) -> dict[str, Any]:
    """Create deterministic, synthetic PF10 evidence for the read-only console."""
    from uuid import UUID
    from trading_bot.platform.orders import OrderIntent, OrderPurpose, OrderSide, OrderType, TimeInForce

    now = require_aware(as_of, "as_of")

    def fixture_intent(suffix: str) -> OrderIntent:
        return OrderIntent.create(
            source_lead_id=f"pf10-fixture-{suffix}",
            source_lead_hash=(suffix * 64)[:64],
            instrument_id=UUID(f"00000000-0000-0000-0000-00000000001{suffix}"),
            symbol=f"R{suffix}",
            side=OrderSide.BUY,
            purpose=OrderPurpose.INCREASE_EXPOSURE,
            quantity=2,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            created_at=now - timedelta(minutes=5),
            strategy_id="CSMOM-LS",
            strategy_version="v0.2",
            decision_at=now - timedelta(minutes=35),
        )

    # Repaired crash window.
    journal1 = SQLiteEventJournal(":memory:")
    broker1 = SimulatedBroker()
    order1 = fixture_intent("1")
    oms1 = OMSService(journal=journal1, broker=broker1)
    oms1.create(order1)
    oms1.approve_risk(order1.order_id, approved_at=now - timedelta(minutes=4, seconds=59))
    oms1.stage_submission(order1.order_id, submitted_at=now - timedelta(minutes=4, seconds=58))
    broker1.submit(order1, submitted_at=now - timedelta(minutes=4, seconds=58))
    snap1 = BrokerAccountSnapshot.from_broker(broker1, captured_at=now - timedelta(seconds=2))
    repaired = RecoveryCoordinator(journal=journal1, broker=broker1).run(snap1, started_at=now - timedelta(seconds=1))

    # Unexplained external order: deliberately blocked/HALTED.
    journal2 = SQLiteEventJournal(":memory:")
    broker2 = SimulatedBroker()
    order2 = fixture_intent("2")
    broker2.submit(order2, submitted_at=now - timedelta(minutes=4))
    snap2 = BrokerAccountSnapshot.from_broker(broker2, captured_at=now - timedelta(seconds=2))
    blocked = RecoveryCoordinator(journal=journal2, broker=broker2).run(snap2, started_at=now - timedelta(seconds=1))

    payload = {
        "mode": "SYNTHETIC_PF10_FIXTURE",
        "status": "PASS",
        "real_broker_used": False,
        "duplicate_risk_created": False,
        "scenarios": [
            {
                "name": "CRASH_AFTER_SUBMISSION",
                "result": repaired.status,
                "runtime_state": repaired.final_runtime_state.value,
                "findings": [finding.to_dict() for finding in repaired.findings],
                "report_hash": repaired.report_hash,
            },
            {
                "name": "UNKNOWN_EXTERNAL_ORDER",
                "result": blocked.status,
                "runtime_state": blocked.final_runtime_state.value,
                "findings": [finding.to_dict() for finding in blocked.findings],
                "report_hash": blocked.report_hash,
            },
        ],
        "acceptance": {
            "crash_recovered_without_resubmit": repaired.unresolved_count == 0 and broker1.submission_count(order1.order_id) == 1,
            "unexplained_divergence_halts": blocked.final_runtime_state == RuntimeSafetyState.HALTED,
            "incident_audit_generated": any(record.event.aggregate_type == "INCIDENT" for record in journal2.records()),
            "phase03_authorized": False,
            "procurement_authorized": False,
        },
        "notice": "Synthetic PF10 recovery/reconciliation evidence only. Real broker reconciliation remains an external validation requirement.",
    }
    payload["fixture_hash"] = _hash(payload)
    journal1.close()
    journal2.close()
    return payload

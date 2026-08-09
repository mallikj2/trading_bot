"""Deterministic alert and incident lifecycle for Phase 02B PF09.

The center is journal-backed and intentionally local/read-only from the web UI.
Alerts are observations of operational/research conditions; they never authorize
orders or mutate strategy logic. Repeated observations are deduplicated by a
stable fingerprint, severity can only escalate while an alert is active, and
incident acknowledgement/resolution is represented by immutable PF03 events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping

from trading_bot.data.time_utils import require_aware
from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.events import DomainEvent, canonical_json


class AlertContractError(ValueError):
    """Raised when alert/incident input violates the PF09 contract."""


class AlertLifecycleError(RuntimeError):
    """Raised for invalid acknowledgement/resolution transitions."""


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return {AlertSeverity.INFO: 1, AlertSeverity.WARNING: 2, AlertSeverity.CRITICAL: 3}[self]


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


def _require_text(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise AlertContractError(f"{name} is required")
    return normalized


def _require_sha256(value: str, name: str) -> str:
    normalized = str(value).lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise AlertContractError(f"{name} must be SHA-256 hex")
    return normalized


def _hash_payload(payload: Mapping[str, Any]) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AlertSignal:
    rule_id: str
    component: str
    entity_id: str
    condition_key: str
    severity: AlertSeverity
    occurred_at: datetime
    title: str
    detail: str
    evidence_hash: str
    incident_key: str
    fingerprint: str
    signal_id: str

    def __post_init__(self) -> None:
        for field_name in ("rule_id", "component", "entity_id", "condition_key", "title", "detail", "incident_key"):
            object.__setattr__(self, field_name, _require_text(getattr(self, field_name), field_name))
        object.__setattr__(self, "occurred_at", require_aware(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "evidence_hash", _require_sha256(self.evidence_hash, "evidence_hash"))
        expected_fingerprint = _hash_payload(self.fingerprint_payload())
        if self.fingerprint != expected_fingerprint:
            raise AlertContractError("fingerprint does not match stable deduplication payload")
        expected_signal = _hash_payload(self.signal_payload())
        if self.signal_id != expected_signal:
            raise AlertContractError("signal_id does not match immutable signal payload")

    @classmethod
    def create(
        cls,
        *,
        rule_id: str,
        component: str,
        entity_id: str,
        condition_key: str,
        severity: AlertSeverity,
        occurred_at: datetime,
        title: str,
        detail: str,
        evidence_hash: str,
        incident_key: str | None = None,
    ) -> "AlertSignal":
        rule = _require_text(rule_id, "rule_id")
        comp = _require_text(component, "component")
        entity = _require_text(entity_id, "entity_id")
        condition = _require_text(condition_key, "condition_key")
        effective_incident_key = _require_text(incident_key or f"{comp}:{entity}", "incident_key")
        occurrence = require_aware(occurred_at, "occurred_at")
        evidence = _require_sha256(evidence_hash, "evidence_hash")
        fingerprint_payload = {
            "rule_id": rule,
            "component": comp,
            "entity_id": entity,
            "condition_key": condition,
            "incident_key": effective_incident_key,
        }
        fingerprint = _hash_payload(fingerprint_payload)
        signal_payload = {
            **fingerprint_payload,
            "fingerprint": fingerprint,
            "severity": severity.value,
            "occurred_at": occurrence.isoformat(),
            "title": _require_text(title, "title"),
            "detail": _require_text(detail, "detail"),
            "evidence_hash": evidence,
        }
        return cls(
            rule_id=rule,
            component=comp,
            entity_id=entity,
            condition_key=condition,
            severity=severity,
            occurred_at=occurrence,
            title=signal_payload["title"],
            detail=signal_payload["detail"],
            evidence_hash=evidence,
            incident_key=effective_incident_key,
            fingerprint=fingerprint,
            signal_id=_hash_payload(signal_payload),
        )

    def fingerprint_payload(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "component": self.component,
            "entity_id": self.entity_id,
            "condition_key": self.condition_key,
            "incident_key": self.incident_key,
        }

    def signal_payload(self) -> dict[str, str]:
        return {
            **self.fingerprint_payload(),
            "fingerprint": self.fingerprint,
            "severity": self.severity.value,
            "occurred_at": self.occurred_at.isoformat(),
            "title": self.title,
            "detail": self.detail,
            "evidence_hash": self.evidence_hash,
        }

    def to_dict(self) -> dict[str, str]:
        return {"signal_id": self.signal_id, **self.signal_payload()}


@dataclass(slots=True)
class _AlertState:
    alert_id: str
    fingerprint: str
    incident_id: str
    rule_id: str
    component: str
    entity_id: str
    condition_key: str
    severity: AlertSeverity
    title: str
    detail: str
    evidence_hash: str
    first_seen_at: datetime
    last_seen_at: datetime
    occurrence_count: int = 1
    status: AlertStatus = AlertStatus.OPEN
    last_event_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "fingerprint": self.fingerprint,
            "incident_id": self.incident_id,
            "rule_id": self.rule_id,
            "component": self.component,
            "entity_id": self.entity_id,
            "condition_key": self.condition_key,
            "severity": self.severity.value,
            "status": self.status.value,
            "title": self.title,
            "detail": self.detail,
            "evidence_hash": self.evidence_hash,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "occurrence_count": self.occurrence_count,
        }


@dataclass(slots=True)
class _IncidentState:
    incident_id: str
    incident_key: str
    opened_at: datetime
    severity: AlertSeverity
    status: IncidentStatus = IncidentStatus.OPEN
    alert_ids: list[str] = field(default_factory=list)
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    acknowledgement_note: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution: str | None = None
    last_event_id: str = ""

    def to_dict(self, alerts: Mapping[str, _AlertState]) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "incident_key": self.incident_key,
            "severity": self.severity.value,
            "status": self.status.value,
            "opened_at": self.opened_at.isoformat(),
            "acknowledged_at": None if self.acknowledged_at is None else self.acknowledged_at.isoformat(),
            "acknowledged_by": self.acknowledged_by,
            "acknowledgement_note": self.acknowledgement_note,
            "resolved_at": None if self.resolved_at is None else self.resolved_at.isoformat(),
            "resolved_by": self.resolved_by,
            "resolution": self.resolution,
            "alerts": [alerts[alert_id].to_dict() for alert_id in self.alert_ids],
        }


@dataclass(frozen=True, slots=True)
class AlertIngestResult:
    action: str
    incident_id: str
    alert_id: str
    journal_event_ids: tuple[str, ...]


class AlertIncidentCenter:
    """Journal-backed deterministic alert and incident projection."""

    PRODUCER = "pf09_alert_incident_center"

    def __init__(self, journal: SQLiteEventJournal) -> None:
        self.journal = journal
        self._alerts: dict[str, _AlertState] = {}
        self._incidents: dict[str, _IncidentState] = {}
        self._active_incident_by_key: dict[str, str] = {}
        self._active_alert_by_fingerprint: dict[str, str] = {}
        self._seen_signal_ids: set[str] = set()
        self._rebuild()

    @property
    def alerts(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            alert.to_dict()
            for alert in sorted(
                self._alerts.values(),
                key=lambda item: (-item.severity.rank, item.status.value, item.first_seen_at, item.alert_id),
            )
        )

    @property
    def incidents(self) -> tuple[dict[str, Any], ...]:
        status_rank = {IncidentStatus.OPEN: 0, IncidentStatus.ACKNOWLEDGED: 1, IncidentStatus.RESOLVED: 2}
        return tuple(
            incident.to_dict(self._alerts)
            for incident in sorted(
                self._incidents.values(),
                key=lambda item: (status_rank[item.status], -item.severity.rank, item.opened_at, item.incident_id),
            )
        )

    def summary(self) -> dict[str, Any]:
        active = [incident for incident in self._incidents.values() if incident.status != IncidentStatus.RESOLVED]
        severity_counts = {severity.value: 0 for severity in AlertSeverity}
        for incident in active:
            severity_counts[incident.severity.value] += 1
        return {
            "active_incident_count": len(active),
            "open_incident_count": sum(1 for item in active if item.status == IncidentStatus.OPEN),
            "acknowledged_incident_count": sum(1 for item in active if item.status == IncidentStatus.ACKNOWLEDGED),
            "resolved_incident_count": sum(1 for item in self._incidents.values() if item.status == IncidentStatus.RESOLVED),
            "active_by_severity": severity_counts,
            "total_alert_count": len(self._alerts),
            "journal_head_hash": self.journal.head_hash,
        }

    def ingest(self, signal: AlertSignal, *, recorded_at: datetime) -> AlertIngestResult:
        recorded = require_aware(recorded_at, "recorded_at")
        if recorded < signal.occurred_at:
            raise AlertContractError("recorded_at cannot precede alert occurrence")
        if signal.signal_id in self._seen_signal_ids:
            active_alert_id = self._active_alert_by_fingerprint.get(signal.fingerprint)
            if active_alert_id is None:
                # The exact observation was already processed in a resolved incident.
                matching = next(
                    (item for item in self._alerts.values() if item.fingerprint == signal.fingerprint), None
                )
                if matching is None:
                    raise AlertLifecycleError("seen signal is missing from rebuilt alert state")
                return AlertIngestResult("DUPLICATE_NOOP", matching.incident_id, matching.alert_id, ())
            alert = self._alerts[active_alert_id]
            return AlertIngestResult("DUPLICATE_NOOP", alert.incident_id, alert.alert_id, ())

        incident = self._find_or_open_incident(signal, recorded_at=recorded)
        existing_alert_id = self._active_alert_by_fingerprint.get(signal.fingerprint)
        events: list[DomainEvent] = []
        if existing_alert_id is None:
            alert_id = _hash_payload(
                {
                    "fingerprint": signal.fingerprint,
                    "incident_id": incident.incident_id,
                    "first_signal_id": signal.signal_id,
                }
            )
            event = DomainEvent.create(
                event_type="ALERT.RAISED",
                aggregate_type="ALERT",
                aggregate_id=alert_id,
                occurred_at=signal.occurred_at,
                correlation_id=incident.incident_id,
                causation_id=incident.last_event_id or None,
                producer=self.PRODUCER,
                payload={
                    **signal.to_dict(),
                    "alert_id": alert_id,
                    "incident_id": incident.incident_id,
                },
            )
            self.journal.append(event, recorded_at=recorded)
            self._apply(event)
            events.append(event)
            self._maybe_reopen_acknowledged_incident(incident.incident_id, signal.severity, signal.occurred_at, recorded, events)
            return AlertIngestResult("RAISED", incident.incident_id, alert_id, tuple(item.event_id for item in events))

        alert = self._alerts[existing_alert_id]
        if alert.incident_id != incident.incident_id:
            raise AlertLifecycleError("active alert fingerprint cannot span active incidents")
        if signal.severity.rank > alert.severity.rank:
            event_type = "ALERT.ESCALATED"
            action = "ESCALATED"
        else:
            event_type = "ALERT.DEDUPLICATED"
            action = "DEDUPLICATED"
        event = DomainEvent.create(
            event_type=event_type,
            aggregate_type="ALERT",
            aggregate_id=alert.alert_id,
            occurred_at=signal.occurred_at,
            correlation_id=incident.incident_id,
            causation_id=alert.last_event_id or incident.last_event_id or None,
            producer=self.PRODUCER,
            payload={
                "alert_id": alert.alert_id,
                "incident_id": incident.incident_id,
                "signal_id": signal.signal_id,
                "fingerprint": signal.fingerprint,
                "observed_severity": signal.severity.value,
                "title": signal.title,
                "detail": signal.detail,
                "evidence_hash": signal.evidence_hash,
                "observed_at": signal.occurred_at.isoformat(),
            },
        )
        self.journal.append(event, recorded_at=recorded)
        self._apply(event)
        events.append(event)
        if event_type == "ALERT.ESCALATED":
            self._maybe_reopen_acknowledged_incident(incident.incident_id, signal.severity, signal.occurred_at, recorded, events)
        return AlertIngestResult(action, incident.incident_id, alert.alert_id, tuple(item.event_id for item in events))

    def acknowledge(
        self,
        incident_id: str,
        *,
        actor: str,
        note: str,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> str:
        incident = self._get_incident(incident_id)
        if incident.status == IncidentStatus.RESOLVED:
            raise AlertLifecycleError("resolved incident cannot be acknowledged")
        if incident.status == IncidentStatus.ACKNOWLEDGED:
            raise AlertLifecycleError("incident is already acknowledged")
        actor_text = _require_text(actor, "actor")
        note_text = _require_text(note, "note")
        occurred = require_aware(occurred_at, "occurred_at")
        recorded = require_aware(recorded_at, "recorded_at")
        if occurred < incident.opened_at or recorded < occurred:
            raise AlertLifecycleError("acknowledgement timestamp is inconsistent with incident history")
        event = DomainEvent.create(
            event_type="INCIDENT.ACKNOWLEDGED",
            aggregate_type="INCIDENT",
            aggregate_id=incident.incident_id,
            occurred_at=occurred,
            correlation_id=incident.incident_id,
            causation_id=incident.last_event_id or None,
            producer=self.PRODUCER,
            payload={"actor": actor_text, "note": note_text},
        )
        self.journal.append(event, recorded_at=recorded)
        self._apply(event)
        return event.event_id

    def resolve(
        self,
        incident_id: str,
        *,
        actor: str,
        resolution: str,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> tuple[str, ...]:
        incident = self._get_incident(incident_id)
        if incident.status == IncidentStatus.RESOLVED:
            raise AlertLifecycleError("incident is already resolved")
        actor_text = _require_text(actor, "actor")
        resolution_text = _require_text(resolution, "resolution")
        occurred = require_aware(occurred_at, "occurred_at")
        recorded = require_aware(recorded_at, "recorded_at")
        if occurred < incident.opened_at or recorded < occurred:
            raise AlertLifecycleError("resolution timestamp is inconsistent with incident history")
        event_ids: list[str] = []
        cause = incident.last_event_id or None
        for alert_id in incident.alert_ids:
            alert = self._alerts[alert_id]
            if alert.status == AlertStatus.RESOLVED:
                continue
            event = DomainEvent.create(
                event_type="ALERT.RESOLVED",
                aggregate_type="ALERT",
                aggregate_id=alert.alert_id,
                occurred_at=occurred,
                correlation_id=incident.incident_id,
                causation_id=cause,
                producer=self.PRODUCER,
                payload={"alert_id": alert.alert_id, "incident_id": incident.incident_id, "actor": actor_text},
            )
            self.journal.append(event, recorded_at=recorded)
            self._apply(event)
            event_ids.append(event.event_id)
            cause = event.event_id
        event = DomainEvent.create(
            event_type="INCIDENT.RESOLVED",
            aggregate_type="INCIDENT",
            aggregate_id=incident.incident_id,
            occurred_at=occurred,
            correlation_id=incident.incident_id,
            causation_id=cause,
            producer=self.PRODUCER,
            payload={"actor": actor_text, "resolution": resolution_text},
        )
        self.journal.append(event, recorded_at=recorded)
        self._apply(event)
        event_ids.append(event.event_id)
        return tuple(event_ids)

    def _find_or_open_incident(self, signal: AlertSignal, *, recorded_at: datetime) -> _IncidentState:
        active_id = self._active_incident_by_key.get(signal.incident_key)
        if active_id is not None:
            return self._incidents[active_id]
        incident_id = _hash_payload(
            {
                "incident_key": signal.incident_key,
                "opened_at": signal.occurred_at.isoformat(),
                "first_signal_id": signal.signal_id,
            }
        )
        event = DomainEvent.create(
            event_type="INCIDENT.OPENED",
            aggregate_type="INCIDENT",
            aggregate_id=incident_id,
            occurred_at=signal.occurred_at,
            correlation_id=incident_id,
            producer=self.PRODUCER,
            payload={
                "incident_id": incident_id,
                "incident_key": signal.incident_key,
                "initial_severity": signal.severity.value,
                "first_signal_id": signal.signal_id,
            },
        )
        self.journal.append(event, recorded_at=recorded_at)
        self._apply(event)
        return self._incidents[incident_id]

    def _maybe_reopen_acknowledged_incident(
        self,
        incident_id: str,
        observed_severity: AlertSeverity,
        occurred_at: datetime,
        recorded_at: datetime,
        events: list[DomainEvent],
    ) -> None:
        incident = self._incidents[incident_id]
        if incident.status != IncidentStatus.ACKNOWLEDGED:
            return
        # New/severity-escalated evidence invalidates the prior human acknowledgement.
        event = DomainEvent.create(
            event_type="INCIDENT.REOPENED",
            aggregate_type="INCIDENT",
            aggregate_id=incident.incident_id,
            occurred_at=occurred_at,
            correlation_id=incident.incident_id,
            causation_id=incident.last_event_id or None,
            producer=self.PRODUCER,
            payload={
                "reason": "NEW_OR_ESCALATED_ALERT_EVIDENCE",
                "observed_severity": observed_severity.value,
            },
        )
        self.journal.append(event, recorded_at=recorded_at)
        self._apply(event)
        events.append(event)

    def _get_incident(self, incident_id: str) -> _IncidentState:
        try:
            return self._incidents[incident_id]
        except KeyError as exc:
            raise AlertLifecycleError("unknown incident_id") from exc

    def _rebuild(self) -> None:
        self._alerts.clear()
        self._incidents.clear()
        self._active_incident_by_key.clear()
        self._active_alert_by_fingerprint.clear()
        self._seen_signal_ids.clear()
        self.journal.verify_integrity()
        for record in self.journal.records():
            if record.event.event_type.startswith("ALERT.") or record.event.event_type.startswith("INCIDENT."):
                self._apply(record.event)

    def _apply(self, event: DomainEvent) -> None:
        payload = event.payload
        if event.event_type == "INCIDENT.OPENED":
            incident = _IncidentState(
                incident_id=event.aggregate_id,
                incident_key=str(payload["incident_key"]),
                opened_at=event.occurred_at,
                severity=AlertSeverity(str(payload["initial_severity"])),
                last_event_id=event.event_id,
            )
            if incident.incident_key in self._active_incident_by_key:
                raise AlertLifecycleError("multiple active incidents share the same incident_key")
            self._incidents[incident.incident_id] = incident
            self._active_incident_by_key[incident.incident_key] = incident.incident_id
            return

        if event.event_type == "ALERT.RAISED":
            signal_id = str(payload["signal_id"])
            fingerprint = str(payload["fingerprint"])
            incident_id = str(payload["incident_id"])
            incident = self._incidents[incident_id]
            alert = _AlertState(
                alert_id=event.aggregate_id,
                fingerprint=fingerprint,
                incident_id=incident_id,
                rule_id=str(payload["rule_id"]),
                component=str(payload["component"]),
                entity_id=str(payload["entity_id"]),
                condition_key=str(payload["condition_key"]),
                severity=AlertSeverity(str(payload["severity"])),
                title=str(payload["title"]),
                detail=str(payload["detail"]),
                evidence_hash=str(payload["evidence_hash"]),
                first_seen_at=event.occurred_at,
                last_seen_at=event.occurred_at,
                last_event_id=event.event_id,
            )
            if fingerprint in self._active_alert_by_fingerprint:
                raise AlertLifecycleError("duplicate active alert fingerprint")
            self._alerts[alert.alert_id] = alert
            self._active_alert_by_fingerprint[fingerprint] = alert.alert_id
            incident.alert_ids.append(alert.alert_id)
            incident.severity = max((self._alerts[item].severity for item in incident.alert_ids), key=lambda sev: sev.rank)
            incident.last_event_id = event.event_id
            self._seen_signal_ids.add(signal_id)
            return

        if event.event_type in {"ALERT.DEDUPLICATED", "ALERT.ESCALATED"}:
            alert = self._alerts[event.aggregate_id]
            signal_id = str(payload["signal_id"])
            observed = AlertSeverity(str(payload["observed_severity"]))
            alert.occurrence_count += 1
            alert.last_seen_at = datetime.fromisoformat(str(payload["observed_at"]))
            alert.title = str(payload["title"])
            alert.detail = str(payload["detail"])
            alert.evidence_hash = str(payload["evidence_hash"])
            if observed.rank > alert.severity.rank:
                alert.severity = observed
            alert.last_event_id = event.event_id
            incident = self._incidents[alert.incident_id]
            incident.severity = max((self._alerts[item].severity for item in incident.alert_ids), key=lambda sev: sev.rank)
            incident.last_event_id = event.event_id
            self._seen_signal_ids.add(signal_id)
            return

        if event.event_type == "INCIDENT.ACKNOWLEDGED":
            incident = self._incidents[event.aggregate_id]
            incident.status = IncidentStatus.ACKNOWLEDGED
            incident.acknowledged_at = event.occurred_at
            incident.acknowledged_by = str(payload["actor"])
            incident.acknowledgement_note = str(payload["note"])
            incident.last_event_id = event.event_id
            return

        if event.event_type == "INCIDENT.REOPENED":
            incident = self._incidents[event.aggregate_id]
            incident.status = IncidentStatus.OPEN
            incident.acknowledged_at = None
            incident.acknowledged_by = None
            incident.acknowledgement_note = None
            incident.last_event_id = event.event_id
            return

        if event.event_type == "ALERT.RESOLVED":
            alert = self._alerts[event.aggregate_id]
            alert.status = AlertStatus.RESOLVED
            alert.last_event_id = event.event_id
            self._active_alert_by_fingerprint.pop(alert.fingerprint, None)
            incident = self._incidents[alert.incident_id]
            incident.last_event_id = event.event_id
            return

        if event.event_type == "INCIDENT.RESOLVED":
            incident = self._incidents[event.aggregate_id]
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = event.occurred_at
            incident.resolved_by = str(payload["actor"])
            incident.resolution = str(payload["resolution"])
            incident.last_event_id = event.event_id
            self._active_incident_by_key.pop(incident.incident_key, None)
            return


def build_pf09_fixture_incident_report(*, as_of: datetime) -> dict[str, Any]:
    """Create deterministic synthetic incident evidence for the read-only console."""
    from datetime import timedelta

    now = require_aware(as_of, "as_of")
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    base_hash = "9" * 64

    data_signal = AlertSignal.create(
        rule_id="DATA_FRESHNESS",
        component="MARKET_DATA",
        entity_id="PF09_FIXTURE_FEED",
        condition_key="STALE_INPUT",
        severity=AlertSeverity.WARNING,
        occurred_at=now - timedelta(minutes=12),
        title="Research feed is stale",
        detail="Synthetic fixture is older than the configured warning threshold.",
        evidence_hash=base_hash,
    )
    center.ingest(data_signal, recorded_at=data_signal.occurred_at)
    repeat = AlertSignal.create(
        rule_id="DATA_FRESHNESS",
        component="MARKET_DATA",
        entity_id="PF09_FIXTURE_FEED",
        condition_key="STALE_INPUT",
        severity=AlertSeverity.WARNING,
        occurred_at=now - timedelta(minutes=10),
        title="Research feed remains stale",
        detail="Repeated synthetic observation was deduplicated into the existing alert.",
        evidence_hash="8" * 64,
    )
    center.ingest(repeat, recorded_at=repeat.occurred_at)

    critical = AlertSignal.create(
        rule_id="JOURNAL_INTEGRITY",
        component="EVENT_JOURNAL",
        entity_id="PF09_FIXTURE_JOURNAL",
        condition_key="INTEGRITY_FAILURE",
        severity=AlertSeverity.CRITICAL,
        occurred_at=now - timedelta(minutes=8),
        title="Journal integrity verification failed",
        detail="Synthetic critical incident for Incident Center rendering only.",
        evidence_hash="7" * 64,
    )
    critical_result = center.ingest(critical, recorded_at=critical.occurred_at)
    center.acknowledge(
        critical_result.incident_id,
        actor="fixture_operator",
        note="Synthetic incident acknowledged for PF09 UI evidence.",
        occurred_at=now - timedelta(minutes=7),
        recorded_at=now - timedelta(minutes=7),
    )

    resolved_signal = AlertSignal.create(
        rule_id="CONFIG_VALIDATION",
        component="CONFIG",
        entity_id="PF09_FIXTURE_CONFIG",
        condition_key="HASH_MISMATCH",
        severity=AlertSeverity.WARNING,
        occurred_at=now - timedelta(minutes=30),
        title="Configuration hash mismatch",
        detail="Synthetic resolved incident used to demonstrate lifecycle history.",
        evidence_hash="6" * 64,
    )
    resolved_result = center.ingest(resolved_signal, recorded_at=resolved_signal.occurred_at)
    center.resolve(
        resolved_result.incident_id,
        actor="fixture_operator",
        resolution="Fixture configuration restored to the expected manifest.",
        occurred_at=now - timedelta(minutes=20),
        recorded_at=now - timedelta(minutes=20),
    )

    report = {
        "mode": "SYNTHETIC_PF09_FIXTURE",
        "status": "PASS",
        "summary": center.summary(),
        "incidents": list(center.incidents),
        "delivery_channels": ["LOCAL_RESEARCH_CONSOLE"],
        "paid_notification_dependency": False,
        "live_notification_delivery_enabled": False,
        "notice": "PF09 synthetic operational evidence only; no external notification service or live broker action.",
    }
    journal.close()
    return report

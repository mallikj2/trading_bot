from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trading_bot.platform.alerts import (
    AlertContractError,
    AlertIncidentCenter,
    AlertLifecycleError,
    AlertSeverity,
    AlertSignal,
)
from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.events import DomainEvent

UTC = timezone.utc
NOW = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)


def signal(
    *,
    minute: int = 0,
    severity: AlertSeverity = AlertSeverity.WARNING,
    rule_id: str = "DATA_FRESHNESS",
    component: str = "DATA",
    entity_id: str = "feed-a",
    condition_key: str = "STALE",
    evidence_char: str = "a",
    incident_key: str | None = None,
) -> AlertSignal:
    return AlertSignal.create(
        rule_id=rule_id,
        component=component,
        entity_id=entity_id,
        condition_key=condition_key,
        severity=severity,
        occurred_at=NOW + timedelta(minutes=minute),
        title=f"{rule_id} {severity.value}",
        detail=f"Observation at minute {minute}",
        evidence_hash=evidence_char * 64,
        incident_key=incident_key,
    )


def test_signal_identity_is_deterministic() -> None:
    first = signal()
    second = signal()
    assert first.signal_id == second.signal_id
    assert first.fingerprint == second.fingerprint


def test_fingerprint_is_stable_across_occurrences_and_severity() -> None:
    first = signal(minute=0, severity=AlertSeverity.WARNING, evidence_char="a")
    second = signal(minute=2, severity=AlertSeverity.CRITICAL, evidence_char="b")
    assert first.fingerprint == second.fingerprint
    assert first.signal_id != second.signal_id


def test_signal_requires_sha256_evidence() -> None:
    with pytest.raises(AlertContractError, match="evidence_hash"):
        AlertSignal.create(
            rule_id="X", component="DATA", entity_id="A", condition_key="BAD",
            severity=AlertSeverity.INFO, occurred_at=NOW, title="x", detail="x", evidence_hash="bad"
        )


def test_first_signal_opens_incident_and_raises_alert() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    result = center.ingest(signal(), recorded_at=NOW)
    assert result.action == "RAISED"
    assert len(result.journal_event_ids) == 1  # INCIDENT.OPENED is journaled internally before this returned alert event.
    assert journal.count == 2
    incident = center.incidents[0]
    assert incident["status"] == "OPEN"
    assert incident["severity"] == "WARNING"
    assert incident["alerts"][0]["occurrence_count"] == 1


def test_exact_signal_reingest_is_noop() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    item = signal()
    center.ingest(item, recorded_at=NOW)
    before = journal.count
    result = center.ingest(item, recorded_at=NOW + timedelta(minutes=1))
    assert result.action == "DUPLICATE_NOOP"
    assert journal.count == before


def test_repeat_observation_is_deduplicated() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    first = center.ingest(signal(), recorded_at=NOW)
    second_signal = signal(minute=2, evidence_char="b")
    second = center.ingest(second_signal, recorded_at=second_signal.occurred_at)
    assert first.alert_id == second.alert_id
    assert second.action == "DEDUPLICATED"
    alert = center.incidents[0]["alerts"][0]
    assert alert["occurrence_count"] == 2
    assert alert["last_seen_at"] == second_signal.occurred_at.isoformat()


def test_severity_escalates_but_never_downgrades() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    center.ingest(signal(severity=AlertSeverity.WARNING), recorded_at=NOW)
    critical = signal(minute=1, severity=AlertSeverity.CRITICAL, evidence_char="b")
    result = center.ingest(critical, recorded_at=critical.occurred_at)
    assert result.action == "ESCALATED"
    lower = signal(minute=2, severity=AlertSeverity.INFO, evidence_char="c")
    result2 = center.ingest(lower, recorded_at=lower.occurred_at)
    assert result2.action == "DEDUPLICATED"
    assert center.incidents[0]["severity"] == "CRITICAL"
    assert center.incidents[0]["alerts"][0]["severity"] == "CRITICAL"


def test_related_rules_group_into_same_incident() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    shared = "DATA:feed-a"
    one = signal(rule_id="DATA_FRESHNESS", incident_key=shared)
    two = signal(minute=1, rule_id="DATA_SCHEMA", condition_key="SCHEMA_DRIFT", evidence_char="b", incident_key=shared)
    a = center.ingest(one, recorded_at=one.occurred_at)
    b = center.ingest(two, recorded_at=two.occurred_at)
    assert a.incident_id == b.incident_id
    assert len(center.incidents) == 1
    assert len(center.incidents[0]["alerts"]) == 2


def test_unrelated_components_open_separate_incidents() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    a = signal(component="DATA", entity_id="feed-a")
    b = signal(minute=1, component="BROKER_SIM", entity_id="sim-a", evidence_char="b")
    center.ingest(a, recorded_at=a.occurred_at)
    center.ingest(b, recorded_at=b.occurred_at)
    assert len(center.incidents) == 2


def test_acknowledgement_requires_operator_and_note() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    result = center.ingest(signal(), recorded_at=NOW)
    with pytest.raises(AlertContractError, match="actor"):
        center.acknowledge(result.incident_id, actor="", note="checked", occurred_at=NOW, recorded_at=NOW)
    with pytest.raises(AlertContractError, match="note"):
        center.acknowledge(result.incident_id, actor="operator", note="", occurred_at=NOW, recorded_at=NOW)


def test_acknowledgement_is_immutable_journal_fact() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    result = center.ingest(signal(), recorded_at=NOW)
    event_id = center.acknowledge(
        result.incident_id, actor="operator", note="investigating",
        occurred_at=NOW + timedelta(minutes=1), recorded_at=NOW + timedelta(minutes=1)
    )
    incident = center.incidents[0]
    assert incident["status"] == "ACKNOWLEDGED"
    assert incident["acknowledged_by"] == "operator"
    assert journal.get_by_event_id(event_id) is not None


def test_new_related_alert_after_ack_reopens_incident() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    first = signal(incident_key="DATA:feed-a")
    result = center.ingest(first, recorded_at=first.occurred_at)
    center.acknowledge(
        result.incident_id, actor="operator", note="seen",
        occurred_at=NOW + timedelta(minutes=1), recorded_at=NOW + timedelta(minutes=1)
    )
    second = signal(
        minute=2, rule_id="DATA_SCHEMA", condition_key="DRIFT", evidence_char="b", incident_key="DATA:feed-a"
    )
    outcome = center.ingest(second, recorded_at=second.occurred_at)
    assert outcome.action == "RAISED"
    assert len(outcome.journal_event_ids) == 2  # ALERT.RAISED + INCIDENT.REOPENED
    incident = center.incidents[0]
    assert incident["status"] == "OPEN"
    assert incident["acknowledged_by"] is None


def test_escalation_after_ack_reopens_incident() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    first = signal()
    result = center.ingest(first, recorded_at=first.occurred_at)
    center.acknowledge(
        result.incident_id, actor="operator", note="seen",
        occurred_at=NOW + timedelta(minutes=1), recorded_at=NOW + timedelta(minutes=1)
    )
    critical = signal(minute=2, severity=AlertSeverity.CRITICAL, evidence_char="b")
    center.ingest(critical, recorded_at=critical.occurred_at)
    assert center.incidents[0]["status"] == "OPEN"
    assert center.incidents[0]["severity"] == "CRITICAL"


def test_same_severity_repeat_after_ack_does_not_reset_ack() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    first = signal()
    result = center.ingest(first, recorded_at=first.occurred_at)
    center.acknowledge(
        result.incident_id, actor="operator", note="seen",
        occurred_at=NOW + timedelta(minutes=1), recorded_at=NOW + timedelta(minutes=1)
    )
    repeat = signal(minute=2, evidence_char="b")
    center.ingest(repeat, recorded_at=repeat.occurred_at)
    assert center.incidents[0]["status"] == "ACKNOWLEDGED"


def test_resolution_closes_all_alerts_and_incident() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    first = signal(incident_key="DATA:feed-a")
    result = center.ingest(first, recorded_at=first.occurred_at)
    second = signal(minute=1, rule_id="DATA_SCHEMA", condition_key="DRIFT", evidence_char="b", incident_key="DATA:feed-a")
    center.ingest(second, recorded_at=second.occurred_at)
    event_ids = center.resolve(
        result.incident_id, actor="operator", resolution="data restored",
        occurred_at=NOW + timedelta(minutes=3), recorded_at=NOW + timedelta(minutes=3)
    )
    incident = center.incidents[0]
    assert incident["status"] == "RESOLVED"
    assert incident["resolution"] == "data restored"
    assert all(alert["status"] == "RESOLVED" for alert in incident["alerts"])
    assert len(event_ids) == 3  # 2 alert closures + incident closure


def test_resolved_incident_cannot_be_acknowledged_or_resolved_again() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    result = center.ingest(signal(), recorded_at=NOW)
    center.resolve(
        result.incident_id, actor="operator", resolution="fixed",
        occurred_at=NOW + timedelta(minutes=1), recorded_at=NOW + timedelta(minutes=1)
    )
    with pytest.raises(AlertLifecycleError, match="resolved"):
        center.acknowledge(
            result.incident_id, actor="operator", note="late",
            occurred_at=NOW + timedelta(minutes=2), recorded_at=NOW + timedelta(minutes=2)
        )
    with pytest.raises(AlertLifecycleError, match="already resolved"):
        center.resolve(
            result.incident_id, actor="operator", resolution="again",
            occurred_at=NOW + timedelta(minutes=2), recorded_at=NOW + timedelta(minutes=2)
        )


def test_new_occurrence_after_resolution_opens_new_incident() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    first = signal()
    first_result = center.ingest(first, recorded_at=first.occurred_at)
    center.resolve(
        first_result.incident_id, actor="operator", resolution="fixed",
        occurred_at=NOW + timedelta(minutes=1), recorded_at=NOW + timedelta(minutes=1)
    )
    later = signal(minute=5, evidence_char="c")
    second_result = center.ingest(later, recorded_at=later.occurred_at)
    assert second_result.incident_id != first_result.incident_id
    assert len(center.incidents) == 2
    assert {row["status"] for row in center.incidents} == {"OPEN", "RESOLVED"}


def test_recorded_at_cannot_precede_signal() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    with pytest.raises(AlertContractError, match="recorded_at"):
        center.ingest(signal(), recorded_at=NOW - timedelta(seconds=1))


def test_summary_is_deterministic() -> None:
    journal = SQLiteEventJournal()
    center = AlertIncidentCenter(journal)
    a = signal()
    b = signal(minute=1, component="JOURNAL", entity_id="main", severity=AlertSeverity.CRITICAL, evidence_char="b")
    center.ingest(a, recorded_at=a.occurred_at)
    center.ingest(b, recorded_at=b.occurred_at)
    summary = center.summary()
    assert summary["active_incident_count"] == 2
    assert summary["active_by_severity"] == {"INFO": 0, "WARNING": 1, "CRITICAL": 1}


def test_rebuild_ignores_unrelated_domain_events(tmp_path: Path) -> None:
    path = tmp_path / "events.sqlite3"
    journal = SQLiteEventJournal(path)
    unrelated = DomainEvent.create(
        event_type="TEST.EVENT", aggregate_type="TEST", aggregate_id="x", occurred_at=NOW,
        correlation_id="test-corr", producer="tests", payload={"x": 1}
    )
    journal.append(unrelated, recorded_at=NOW)
    center = AlertIncidentCenter(journal)
    item = signal(minute=1)
    center.ingest(item, recorded_at=item.occurred_at)
    journal.close()

    reopened = SQLiteEventJournal(path)
    rebuilt = AlertIncidentCenter(reopened)
    assert len(rebuilt.incidents) == 1
    assert rebuilt.summary()["total_alert_count"] == 1

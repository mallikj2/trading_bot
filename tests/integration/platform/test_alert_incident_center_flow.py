from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from trading_bot.platform.alerts import AlertIncidentCenter, AlertSeverity, AlertSignal
from trading_bot.platform.event_journal import SQLiteEventJournal

UTC = timezone.utc
NOW = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)


def _signal(*, minutes: int, severity: AlertSeverity, evidence: str) -> AlertSignal:
    return AlertSignal.create(
        rule_id="JOURNAL_INTEGRITY",
        component="EVENT_JOURNAL",
        entity_id="local-main",
        condition_key="VERIFY_FAILURE",
        severity=severity,
        occurred_at=NOW + timedelta(minutes=minutes),
        title="Journal verification state",
        detail=f"Synthetic evidence {evidence}",
        evidence_hash=evidence * 64,
    )


def test_restart_rebuilds_identical_incident_projection(tmp_path: Path) -> None:
    path = tmp_path / "pf09.sqlite3"
    journal = SQLiteEventJournal(path)
    center = AlertIncidentCenter(journal)
    first = _signal(minutes=0, severity=AlertSeverity.WARNING, evidence="a")
    result = center.ingest(first, recorded_at=first.occurred_at)
    center.acknowledge(
        result.incident_id, actor="operator", note="investigating",
        occurred_at=NOW + timedelta(minutes=1), recorded_at=NOW + timedelta(minutes=1)
    )
    escalated = _signal(minutes=2, severity=AlertSeverity.CRITICAL, evidence="b")
    center.ingest(escalated, recorded_at=escalated.occurred_at)
    expected_incidents = center.incidents
    expected_alerts = center.alerts
    expected_summary = center.summary()
    expected_head = journal.head_hash
    journal.close()

    reopened = SQLiteEventJournal(path)
    rebuilt = AlertIncidentCenter(reopened)
    assert rebuilt.incidents == expected_incidents
    assert rebuilt.alerts == expected_alerts
    assert rebuilt.summary() == expected_summary
    assert reopened.head_hash == expected_head
    assert reopened.verify_integrity() == expected_head


def test_complete_lifecycle_is_append_only_and_replayable(tmp_path: Path) -> None:
    path = tmp_path / "lifecycle.sqlite3"
    journal = SQLiteEventJournal(path)
    center = AlertIncidentCenter(journal)
    first = _signal(minutes=0, severity=AlertSeverity.WARNING, evidence="a")
    result = center.ingest(first, recorded_at=first.occurred_at)
    repeat = _signal(minutes=1, severity=AlertSeverity.WARNING, evidence="b")
    center.ingest(repeat, recorded_at=repeat.occurred_at)
    center.acknowledge(
        result.incident_id, actor="operator", note="triaged",
        occurred_at=NOW + timedelta(minutes=2), recorded_at=NOW + timedelta(minutes=2)
    )
    critical = _signal(minutes=3, severity=AlertSeverity.CRITICAL, evidence="c")
    center.ingest(critical, recorded_at=critical.occurred_at)
    center.resolve(
        result.incident_id, actor="operator", resolution="journal restored and verified",
        occurred_at=NOW + timedelta(minutes=4), recorded_at=NOW + timedelta(minutes=4)
    )
    assert center.incidents[0]["status"] == "RESOLVED"
    event_types = [record.event.event_type for record in journal.records()]
    assert event_types == [
        "INCIDENT.OPENED",
        "ALERT.RAISED",
        "ALERT.DEDUPLICATED",
        "INCIDENT.ACKNOWLEDGED",
        "ALERT.ESCALATED",
        "INCIDENT.REOPENED",
        "ALERT.RESOLVED",
        "INCIDENT.RESOLVED",
    ]
    journal.verify_integrity()

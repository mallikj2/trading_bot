from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from trading_bot.platform.api.research_api import create_app
from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.replay import ReplayEngine
from trading_bot.platform.research_console import build_fixture_console
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

UTC = timezone.utc
NOW = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)


def obs(status: ProtectionStatus, at: datetime, hash_char: str) -> ProtectionObservation:
    return ProtectionObservation(
        "JOURNAL_INTEGRITY",
        ProtectionScope.JOURNAL,
        status,
        at,
        at,
        at + timedelta(hours=1),
        f"JOURNAL_{status.value}",
        f"journal status {status.value}",
        hash_char * 64,
    )


def test_safety_transitions_journal_and_replay_deterministically(tmp_path) -> None:
    engine = ProtectionEngine((StatusProtectionRule("JOURNAL_INTEGRITY", ProtectionScope.JOURNAL),))
    machine = RuntimeSafetyMachine()
    journal = SQLiteEventJournal(tmp_path / "runtime.sqlite3")

    degraded = engine.evaluate((obs(ProtectionStatus.DEGRADED, NOW, "a"),), evaluated_at=NOW)
    eval_event = protection_evaluated_event(degraded)
    journal.append(eval_event, recorded_at=NOW + timedelta(seconds=1))
    transition = machine.apply(degraded).transition
    assert transition is not None
    transition_event = runtime_safety_transition_event(transition, causation_id=eval_event.event_id)
    journal.append(transition_event, recorded_at=NOW + timedelta(seconds=2))

    healthy_at = NOW + timedelta(minutes=1)
    healthy = engine.evaluate((obs(ProtectionStatus.HEALTHY, healthy_at, "b"),), evaluated_at=healthy_at)
    healthy_event = protection_evaluated_event(healthy)
    journal.append(healthy_event, recorded_at=healthy_at + timedelta(seconds=1))
    approval = RecoveryApproval("approval-restore", healthy_at + timedelta(seconds=2), RuntimeSafetyState.ACTIVE, "operator", "journal verified", "c"*64)
    recovered = machine.apply(healthy, recovery_approval=approval).transition
    assert recovered is not None
    recovery_event = runtime_safety_transition_event(recovered, causation_id=healthy_event.event_id)
    journal.append(recovery_event, recorded_at=healthy_at + timedelta(seconds=3))

    result = ReplayEngine(RuntimeSafetyProjector()).replay_journal(journal)
    assert result.snapshot["state"] == "ACTIVE"
    assert result.snapshot["transition_ids"] == [transition.transition_id, recovered.transition_id]
    first_hash = result.state_hash
    journal.close()

    reopened = SQLiteEventJournal(tmp_path / "runtime.sqlite3")
    replayed = ReplayEngine(RuntimeSafetyProjector()).replay_journal(reopened)
    assert replayed.state_hash == first_hash
    assert replayed.snapshot == result.snapshot


def test_research_console_exposes_protections_but_remains_governance_read_only() -> None:
    with TestClient(create_app(build_fixture_console())) as client:
        risk = client.get("/api/v1/risk").json()
        assert risk["runtime_state"] == "ACTIVE"
        assert risk["new_risk_allowed"] is False
        assert risk["runtime_permissions"]["simulate_increase_exposure"] is True
        assert risk["runtime_permissions"]["mutate_broker"] is False
        assert {row["protection_id"] for row in risk["protections"]} == {
            "JOURNAL_INTEGRITY",
            "CONFIG_INTEGRITY",
            "RESEARCH_DATA_FRESHNESS",
        }
        assert all(row["required_state"] == "ACTIVE" for row in risk["protections"])
        for method in (client.post, client.put, client.patch, client.delete):
            assert method("/api/v1/risk").status_code == 405

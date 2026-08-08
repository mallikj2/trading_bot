from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trading_bot.platform.runtime_safety import (
    ProtectionEngine,
    ProtectionObservation,
    ProtectionScope,
    ProtectionStatus,
    RecoveryApproval,
    RuntimeSafetyError,
    RuntimeSafetyMachine,
    RuntimeSafetyState,
    StatusProtectionRule,
    StalenessProtectionRule,
    permissions_for,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)
HASH = "a" * 64


def observation(
    protection_id: str,
    scope: ProtectionScope,
    status: ProtectionStatus = ProtectionStatus.HEALTHY,
    *,
    observed_at: datetime = NOW,
    available_at: datetime = NOW,
    expires_at: datetime = NOW + timedelta(hours=1),
    evidence_hash: str = HASH,
) -> ProtectionObservation:
    return ProtectionObservation(
        protection_id=protection_id,
        scope=scope,
        status=status,
        observed_at=observed_at,
        available_at=available_at,
        expires_at=expires_at,
        reason_code=f"{protection_id}_{status.value}",
        detail=f"{protection_id} is {status.value.lower()}.",
        evidence_hash=evidence_hash,
    )


def test_status_rule_maps_health_to_runtime_state() -> None:
    rule = StatusProtectionRule("DATA", ProtectionScope.DATA)
    assert rule.evaluate(observation("DATA", ProtectionScope.DATA), evaluated_at=NOW).required_state == RuntimeSafetyState.ACTIVE
    assert rule.evaluate(observation("DATA", ProtectionScope.DATA, ProtectionStatus.DEGRADED), evaluated_at=NOW).required_state == RuntimeSafetyState.REDUCING
    assert rule.evaluate(observation("DATA", ProtectionScope.DATA, ProtectionStatus.FAILED), evaluated_at=NOW).required_state == RuntimeSafetyState.HALTED
    assert rule.evaluate(observation("DATA", ProtectionScope.DATA, ProtectionStatus.UNKNOWN), evaluated_at=NOW).required_state == RuntimeSafetyState.HALTED


def test_missing_required_protection_fails_closed() -> None:
    engine = ProtectionEngine((StatusProtectionRule("JOURNAL", ProtectionScope.JOURNAL),))
    evaluation = engine.evaluate((), evaluated_at=NOW)
    assert evaluation.required_state == RuntimeSafetyState.HALTED
    assert evaluation.decisions[0].reason_code == "MISSING_PROTECTION_EVIDENCE"


def test_future_observation_is_not_visible() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    future = observation("DATA", ProtectionScope.DATA, available_at=NOW + timedelta(minutes=1), expires_at=NOW + timedelta(hours=1))
    evaluation = engine.evaluate((future,), evaluated_at=NOW)
    assert evaluation.required_state == RuntimeSafetyState.HALTED
    assert evaluation.decisions[0].observation_hash is None


def test_expired_status_evidence_halts() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    expired = observation("DATA", ProtectionScope.DATA, observed_at=NOW - timedelta(hours=2), available_at=NOW - timedelta(hours=2), expires_at=NOW)
    evaluation = engine.evaluate((expired,), evaluated_at=NOW)
    assert evaluation.required_state == RuntimeSafetyState.HALTED
    assert evaluation.decisions[0].reason_code == "STALE_PROTECTION_EVIDENCE"


def test_staleness_rule_has_active_reducing_halted_bands() -> None:
    rule = StalenessProtectionRule("FEED", ProtectionScope.DATA, timedelta(minutes=5), timedelta(minutes=15))
    active = observation("FEED", ProtectionScope.DATA, observed_at=NOW - timedelta(minutes=5), available_at=NOW - timedelta(minutes=5))
    reducing = observation("FEED", ProtectionScope.DATA, observed_at=NOW - timedelta(minutes=6), available_at=NOW - timedelta(minutes=6))
    halted = observation("FEED", ProtectionScope.DATA, observed_at=NOW - timedelta(minutes=16), available_at=NOW - timedelta(minutes=16))
    assert rule.evaluate(active, evaluated_at=NOW).required_state == RuntimeSafetyState.ACTIVE
    assert rule.evaluate(reducing, evaluated_at=NOW).required_state == RuntimeSafetyState.REDUCING
    assert rule.evaluate(halted, evaluated_at=NOW).required_state == RuntimeSafetyState.HALTED


def test_staleness_rule_does_not_override_failed_source_status() -> None:
    rule = StalenessProtectionRule("FEED", ProtectionScope.DATA, timedelta(minutes=5), timedelta(minutes=15))
    failed = observation(
        "FEED", ProtectionScope.DATA, ProtectionStatus.FAILED,
        observed_at=NOW, available_at=NOW, expires_at=NOW + timedelta(hours=1),
    )
    decision = rule.evaluate(failed, evaluated_at=NOW)
    assert decision.required_state == RuntimeSafetyState.HALTED
    assert decision.reason_code == "FEED_FAILED"


def test_protection_engine_chooses_most_restrictive_decision() -> None:
    engine = ProtectionEngine((
        StatusProtectionRule("JOURNAL", ProtectionScope.JOURNAL),
        StatusProtectionRule("CONFIG", ProtectionScope.CONFIG),
    ))
    evaluation = engine.evaluate((
        observation("JOURNAL", ProtectionScope.JOURNAL, ProtectionStatus.DEGRADED),
        observation("CONFIG", ProtectionScope.CONFIG, ProtectionStatus.FAILED, evidence_hash="b" * 64),
    ), evaluated_at=NOW)
    assert evaluation.required_state == RuntimeSafetyState.HALTED
    assert set(evaluation.reason_codes) == {"CONFIG_FAILED", "JOURNAL_DEGRADED"}


def test_same_time_conflicting_evidence_is_rejected() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    first = observation("DATA", ProtectionScope.DATA, ProtectionStatus.HEALTHY, evidence_hash="a" * 64)
    second = observation("DATA", ProtectionScope.DATA, ProtectionStatus.FAILED, evidence_hash="b" * 64)
    with pytest.raises(RuntimeSafetyError, match="conflicting same-time"):
        engine.evaluate((first, second), evaluated_at=NOW)


def test_unregistered_protection_evidence_is_rejected() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    with pytest.raises(RuntimeSafetyError, match="unregistered"):
        engine.evaluate((observation("BROKER", ProtectionScope.BROKER),), evaluated_at=NOW)


def test_automatic_escalation_active_to_reducing() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    evaluation = engine.evaluate((observation("DATA", ProtectionScope.DATA, ProtectionStatus.DEGRADED),), evaluated_at=NOW)
    machine = RuntimeSafetyMachine()
    update = machine.apply(evaluation)
    assert update.state == RuntimeSafetyState.REDUCING
    assert update.transition is not None
    assert update.transition.trigger.value == "AUTOMATIC_ESCALATION"
    assert not update.permissions.simulate_increase_exposure
    assert update.permissions.reduce_exposure


def test_automatic_escalation_reaches_halted() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    machine = RuntimeSafetyMachine()
    machine.apply(engine.evaluate((observation("DATA", ProtectionScope.DATA, ProtectionStatus.DEGRADED),), evaluated_at=NOW))
    halted_eval = engine.evaluate((observation("DATA", ProtectionScope.DATA, ProtectionStatus.FAILED, available_at=NOW + timedelta(minutes=1), observed_at=NOW + timedelta(minutes=1), expires_at=NOW + timedelta(hours=1), evidence_hash="b"*64),), evaluated_at=NOW + timedelta(minutes=1))
    update = machine.apply(halted_eval)
    assert update.state == RuntimeSafetyState.HALTED
    assert not update.permissions.reduce_exposure
    assert update.permissions.cancel_open_orders


def test_recovery_never_happens_automatically() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    machine = RuntimeSafetyMachine(RuntimeSafetyState.HALTED)
    healthy = engine.evaluate((observation("DATA", ProtectionScope.DATA),), evaluated_at=NOW)
    update = machine.apply(healthy)
    assert update.state == RuntimeSafetyState.HALTED
    assert update.transition is None
    assert update.recovery_required


def test_explicit_recovery_requires_current_evaluation_acknowledgement() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    machine = RuntimeSafetyMachine(RuntimeSafetyState.HALTED)
    healthy = engine.evaluate((observation("DATA", ProtectionScope.DATA),), evaluated_at=NOW)
    stale = RecoveryApproval("approval-1", NOW - timedelta(seconds=1), RuntimeSafetyState.ACTIVE, "operator", "verified", "c"*64)
    with pytest.raises(RuntimeSafetyError, match="acknowledge"):
        machine.apply(healthy, recovery_approval=stale)


def test_explicit_recovery_to_evaluated_state() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    machine = RuntimeSafetyMachine(RuntimeSafetyState.HALTED)
    healthy = engine.evaluate((observation("DATA", ProtectionScope.DATA),), evaluated_at=NOW)
    approval = RecoveryApproval("approval-1", NOW + timedelta(seconds=1), RuntimeSafetyState.ACTIVE, "operator", "all protections healthy", "c"*64)
    update = machine.apply(healthy, recovery_approval=approval)
    assert update.state == RuntimeSafetyState.ACTIVE
    assert update.transition is not None
    assert update.transition.trigger.value == "EXPLICIT_RECOVERY"
    assert update.transition.recovery_approval_id == "approval-1"


def test_recovery_approval_cannot_target_wrong_state() -> None:
    engine = ProtectionEngine((StatusProtectionRule("DATA", ProtectionScope.DATA),))
    machine = RuntimeSafetyMachine(RuntimeSafetyState.HALTED)
    healthy = engine.evaluate((observation("DATA", ProtectionScope.DATA),), evaluated_at=NOW)
    approval = RecoveryApproval("approval-1", NOW + timedelta(seconds=1), RuntimeSafetyState.REDUCING, "operator", "wrong target", "c"*64)
    with pytest.raises(RuntimeSafetyError, match="target"):
        machine.apply(healthy, recovery_approval=approval)


def test_permissions_are_fail_closed_by_state() -> None:
    assert permissions_for(RuntimeSafetyState.ACTIVE).simulate_increase_exposure
    assert not permissions_for(RuntimeSafetyState.REDUCING).simulate_increase_exposure
    assert permissions_for(RuntimeSafetyState.REDUCING).reduce_exposure
    assert not permissions_for(RuntimeSafetyState.HALTED).reduce_exposure
    assert permissions_for(RuntimeSafetyState.HALTED).cancel_open_orders
    for state in RuntimeSafetyState:
        assert not permissions_for(state).mutate_broker


def test_runtime_safety_module_does_not_embed_alpha_rules() -> None:
    source = Path(__file__).parents[3] / "src/trading_bot/platform/runtime_safety.py"
    text = source.read_text()
    for forbidden in ("MOM12", "MOM6", "SMA200", "score >=", "0.75"):
        assert forbidden not in text

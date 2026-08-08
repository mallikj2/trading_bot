"""Deterministic runtime-safety state and operational protections for PF04.

This module is deliberately broker-agnostic and strategy-agnostic. Protections
may restrict runtime permissions, but they do not alter alpha formulas,
universe rules, ranking thresholds, or TradeLead scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping, Protocol

from trading_bot.data.time_utils import require_aware
from trading_bot.platform.events import DomainEvent, canonical_json


class RuntimeSafetyError(ValueError):
    """Raised when runtime safety evidence or a transition is invalid."""


class RuntimeSafetyState(str, Enum):
    ACTIVE = "ACTIVE"
    REDUCING = "REDUCING"
    HALTED = "HALTED"


_STATE_RANK = {
    RuntimeSafetyState.ACTIVE: 0,
    RuntimeSafetyState.REDUCING: 1,
    RuntimeSafetyState.HALTED: 2,
}


class ProtectionStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ProtectionScope(str, Enum):
    DATA = "DATA"
    JOURNAL = "JOURNAL"
    CONFIG = "CONFIG"
    BROKER = "BROKER"
    RECONCILIATION = "RECONCILIATION"
    PORTFOLIO = "PORTFOLIO"
    MARKET = "MARKET"
    PLATFORM = "PLATFORM"


class TransitionTrigger(str, Enum):
    AUTOMATIC_ESCALATION = "AUTOMATIC_ESCALATION"
    EXPLICIT_RECOVERY = "EXPLICIT_RECOVERY"


@dataclass(frozen=True, slots=True)
class RuntimePermissions:
    simulate_increase_exposure: bool
    reduce_exposure: bool
    cancel_open_orders: bool
    mutate_broker: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "simulate_increase_exposure": self.simulate_increase_exposure,
            "reduce_exposure": self.reduce_exposure,
            "cancel_open_orders": self.cancel_open_orders,
            "mutate_broker": self.mutate_broker,
        }


def permissions_for(state: RuntimeSafetyState) -> RuntimePermissions:
    if state == RuntimeSafetyState.ACTIVE:
        return RuntimePermissions(True, True, True, False)
    if state == RuntimeSafetyState.REDUCING:
        return RuntimePermissions(False, True, True, False)
    return RuntimePermissions(False, False, True, False)


@dataclass(frozen=True, slots=True)
class ProtectionObservation:
    protection_id: str
    scope: ProtectionScope
    status: ProtectionStatus
    observed_at: datetime
    available_at: datetime
    expires_at: datetime
    reason_code: str
    detail: str
    evidence_hash: str

    def __post_init__(self) -> None:
        for name in ("observed_at", "available_at", "expires_at"):
            require_aware(getattr(self, name), name)
        if not self.protection_id.strip():
            raise RuntimeSafetyError("protection_id is required")
        if not self.reason_code.strip() or not self.detail.strip():
            raise RuntimeSafetyError("reason_code and detail are required")
        if len(self.evidence_hash) != 64 or any(ch not in "0123456789abcdef" for ch in self.evidence_hash):
            raise RuntimeSafetyError("evidence_hash must be lowercase SHA-256 hex")
        if self.available_at < self.observed_at:
            raise RuntimeSafetyError("available_at cannot precede observed_at")
        if self.expires_at <= self.available_at:
            raise RuntimeSafetyError("expires_at must be later than available_at")

    @property
    def content_hash(self) -> str:
        return sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, str]:
        return {
            "protection_id": self.protection_id,
            "scope": self.scope.value,
            "status": self.status.value,
            "observed_at": self.observed_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "reason_code": self.reason_code,
            "detail": self.detail,
            "evidence_hash": self.evidence_hash,
        }


@dataclass(frozen=True, slots=True)
class ProtectionDecision:
    protection_id: str
    scope: ProtectionScope
    evaluated_at: datetime
    required_state: RuntimeSafetyState
    reason_code: str
    detail: str
    observation_hash: str | None

    def __post_init__(self) -> None:
        require_aware(self.evaluated_at, "evaluated_at")
        if not self.protection_id.strip() or not self.reason_code.strip() or not self.detail.strip():
            raise RuntimeSafetyError("protection decision identifiers and detail are required")
        if self.observation_hash is not None and (
            len(self.observation_hash) != 64
            or any(ch not in "0123456789abcdef" for ch in self.observation_hash)
        ):
            raise RuntimeSafetyError("observation_hash must be lowercase SHA-256 hex when supplied")

    @property
    def active(self) -> bool:
        return self.required_state != RuntimeSafetyState.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "protection_id": self.protection_id,
            "scope": self.scope.value,
            "evaluated_at": self.evaluated_at.isoformat(),
            "required_state": self.required_state.value,
            "reason_code": self.reason_code,
            "detail": self.detail,
            "observation_hash": self.observation_hash,
            "active": self.active,
        }


class ProtectionRule(Protocol):
    protection_id: str
    scope: ProtectionScope

    def evaluate(
        self,
        observation: ProtectionObservation | None,
        *,
        evaluated_at: datetime,
    ) -> ProtectionDecision: ...


@dataclass(frozen=True, slots=True)
class StatusProtectionRule:
    protection_id: str
    scope: ProtectionScope

    def evaluate(
        self,
        observation: ProtectionObservation | None,
        *,
        evaluated_at: datetime,
    ) -> ProtectionDecision:
        require_aware(evaluated_at, "evaluated_at")
        if observation is None:
            return ProtectionDecision(
                self.protection_id,
                self.scope,
                evaluated_at,
                RuntimeSafetyState.HALTED,
                "MISSING_PROTECTION_EVIDENCE",
                f"No point-in-time evidence is available for required protection {self.protection_id}.",
                None,
            )
        if observation.protection_id != self.protection_id or observation.scope != self.scope:
            raise RuntimeSafetyError("observation does not match protection rule")
        if observation.available_at > evaluated_at:
            raise RuntimeSafetyError("future protection evidence cannot be used")
        if evaluated_at >= observation.expires_at:
            return ProtectionDecision(
                self.protection_id,
                self.scope,
                evaluated_at,
                RuntimeSafetyState.HALTED,
                "STALE_PROTECTION_EVIDENCE",
                f"Protection evidence for {self.protection_id} expired before evaluation.",
                observation.content_hash,
            )
        state = {
            ProtectionStatus.HEALTHY: RuntimeSafetyState.ACTIVE,
            ProtectionStatus.DEGRADED: RuntimeSafetyState.REDUCING,
            ProtectionStatus.FAILED: RuntimeSafetyState.HALTED,
            ProtectionStatus.UNKNOWN: RuntimeSafetyState.HALTED,
        }[observation.status]
        return ProtectionDecision(
            self.protection_id,
            self.scope,
            evaluated_at,
            state,
            observation.reason_code,
            observation.detail,
            observation.content_hash,
        )


@dataclass(frozen=True, slots=True)
class StalenessProtectionRule:
    """Operational freshness rule using observed_at age, not market alpha."""

    protection_id: str
    scope: ProtectionScope
    reduce_after: timedelta
    halt_after: timedelta

    def __post_init__(self) -> None:
        if self.reduce_after <= timedelta(0):
            raise RuntimeSafetyError("reduce_after must be positive")
        if self.halt_after <= self.reduce_after:
            raise RuntimeSafetyError("halt_after must exceed reduce_after")

    def evaluate(
        self,
        observation: ProtectionObservation | None,
        *,
        evaluated_at: datetime,
    ) -> ProtectionDecision:
        require_aware(evaluated_at, "evaluated_at")
        if observation is None:
            return ProtectionDecision(
                self.protection_id,
                self.scope,
                evaluated_at,
                RuntimeSafetyState.HALTED,
                "MISSING_FRESHNESS_EVIDENCE",
                f"No freshness observation is available for {self.protection_id}.",
                None,
            )
        if observation.protection_id != self.protection_id or observation.scope != self.scope:
            raise RuntimeSafetyError("observation does not match staleness rule")
        if observation.available_at > evaluated_at or observation.observed_at > evaluated_at:
            raise RuntimeSafetyError("future freshness evidence cannot be used")
        if evaluated_at >= observation.expires_at:
            age_state = RuntimeSafetyState.HALTED
            age_reason = "FRESHNESS_EVIDENCE_EXPIRED"
        else:
            age = evaluated_at - observation.observed_at
            if age > self.halt_after:
                age_state = RuntimeSafetyState.HALTED
                age_reason = "DATA_TOO_STALE"
            elif age > self.reduce_after:
                age_state = RuntimeSafetyState.REDUCING
                age_reason = "DATA_FRESHNESS_DEGRADED"
            else:
                age_state = RuntimeSafetyState.ACTIVE
                age_reason = observation.reason_code
        status_state = {
            ProtectionStatus.HEALTHY: RuntimeSafetyState.ACTIVE,
            ProtectionStatus.DEGRADED: RuntimeSafetyState.REDUCING,
            ProtectionStatus.FAILED: RuntimeSafetyState.HALTED,
            ProtectionStatus.UNKNOWN: RuntimeSafetyState.HALTED,
        }[observation.status]
        if _STATE_RANK[status_state] >= _STATE_RANK[age_state]:
            state = status_state
            reason = observation.reason_code
        else:
            state = age_state
            reason = age_reason
        return ProtectionDecision(
            self.protection_id,
            self.scope,
            evaluated_at,
            state,
            reason,
            observation.detail,
            observation.content_hash,
        )


@dataclass(frozen=True, slots=True)
class ProtectionEvaluation:
    evaluated_at: datetime
    decisions: tuple[ProtectionDecision, ...]
    required_state: RuntimeSafetyState

    def __post_init__(self) -> None:
        require_aware(self.evaluated_at, "evaluated_at")
        if not self.decisions:
            raise RuntimeSafetyError("protection evaluation requires at least one decision")
        expected = max(self.decisions, key=lambda item: _STATE_RANK[item.required_state]).required_state
        if expected != self.required_state:
            raise RuntimeSafetyError("required_state must equal the most restrictive decision")

    @property
    def evaluation_hash(self) -> str:
        return sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                decision.reason_code
                for decision in self.decisions
                if decision.required_state != RuntimeSafetyState.ACTIVE
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_at": self.evaluated_at.isoformat(),
            "required_state": self.required_state.value,
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


class ProtectionEngine:
    """Evaluate a fixed required protection set with point-in-time evidence."""

    def __init__(self, rules: Iterable[ProtectionRule]) -> None:
        materialized = tuple(rules)
        if not materialized:
            raise RuntimeSafetyError("at least one protection rule is required")
        ids = [rule.protection_id for rule in materialized]
        if len(set(ids)) != len(ids):
            raise RuntimeSafetyError("protection rule IDs must be unique")
        self._rules = materialized
        self._rule_ids = frozenset(ids)

    @property
    def protection_ids(self) -> tuple[str, ...]:
        return tuple(rule.protection_id for rule in self._rules)

    def evaluate(
        self,
        observations: Iterable[ProtectionObservation],
        *,
        evaluated_at: datetime,
    ) -> ProtectionEvaluation:
        require_aware(evaluated_at, "evaluated_at")
        by_id: dict[str, list[ProtectionObservation]] = {}
        for observation in observations:
            if observation.protection_id not in self._rule_ids:
                raise RuntimeSafetyError(f"unregistered protection evidence: {observation.protection_id}")
            if observation.available_at > evaluated_at:
                continue
            by_id.setdefault(observation.protection_id, []).append(observation)

        selected: dict[str, ProtectionObservation] = {}
        for protection_id, candidates in by_id.items():
            candidates.sort(key=lambda item: (item.available_at, item.observed_at, item.content_hash))
            latest = candidates[-1]
            peers = [item for item in candidates if item.available_at == latest.available_at]
            distinct = {item.content_hash for item in peers}
            if len(distinct) > 1:
                raise RuntimeSafetyError(
                    f"conflicting same-time protection evidence for {protection_id}"
                )
            selected[protection_id] = latest

        decisions = tuple(
            rule.evaluate(selected.get(rule.protection_id), evaluated_at=evaluated_at)
            for rule in self._rules
        )
        required = max(decisions, key=lambda item: _STATE_RANK[item.required_state]).required_state
        return ProtectionEvaluation(evaluated_at, decisions, required)


@dataclass(frozen=True, slots=True)
class RecoveryApproval:
    approval_id: str
    approved_at: datetime
    target_state: RuntimeSafetyState
    approved_by: str
    reason: str
    evidence_hash: str

    def __post_init__(self) -> None:
        require_aware(self.approved_at, "approved_at")
        if not self.approval_id.strip() or not self.approved_by.strip() or not self.reason.strip():
            raise RuntimeSafetyError("recovery approval metadata is required")
        if len(self.evidence_hash) != 64 or any(
            ch not in "0123456789abcdef" for ch in self.evidence_hash
        ):
            raise RuntimeSafetyError("recovery evidence_hash must be lowercase SHA-256 hex")


@dataclass(frozen=True, slots=True)
class RuntimeSafetyTransition:
    transition_id: str
    from_state: RuntimeSafetyState
    to_state: RuntimeSafetyState
    changed_at: datetime
    trigger: TransitionTrigger
    evaluation_hash: str
    reason_codes: tuple[str, ...]
    recovery_approval_id: str | None = None

    def __post_init__(self) -> None:
        require_aware(self.changed_at, "changed_at")
        if self.from_state == self.to_state:
            raise RuntimeSafetyError("runtime safety transition must change state")
        for name in ("transition_id", "evaluation_hash"):
            value = getattr(self, name)
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise RuntimeSafetyError(f"{name} must be lowercase SHA-256 hex")
        if self.trigger == TransitionTrigger.AUTOMATIC_ESCALATION:
            if _STATE_RANK[self.to_state] <= _STATE_RANK[self.from_state]:
                raise RuntimeSafetyError("automatic transitions may only escalate restrictions")
            if self.recovery_approval_id is not None:
                raise RuntimeSafetyError("automatic escalation cannot carry recovery approval")
        else:
            if _STATE_RANK[self.to_state] >= _STATE_RANK[self.from_state]:
                raise RuntimeSafetyError("explicit recovery must reduce restrictions")
            if not self.recovery_approval_id:
                raise RuntimeSafetyError("explicit recovery requires approval ID")

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "changed_at": self.changed_at.isoformat(),
            "trigger": self.trigger.value,
            "evaluation_hash": self.evaluation_hash,
            "reason_codes": list(self.reason_codes),
            "recovery_approval_id": self.recovery_approval_id,
        }


@dataclass(frozen=True, slots=True)
class SafetyUpdate:
    state: RuntimeSafetyState
    transition: RuntimeSafetyTransition | None
    recovery_required: bool
    required_state: RuntimeSafetyState
    permissions: RuntimePermissions


class RuntimeSafetyMachine:
    """Small deterministic state machine with automatic escalation/manual recovery."""

    def __init__(self, initial_state: RuntimeSafetyState = RuntimeSafetyState.ACTIVE) -> None:
        self._state = initial_state
        self._history: list[RuntimeSafetyTransition] = []

    @property
    def state(self) -> RuntimeSafetyState:
        return self._state

    @property
    def history(self) -> tuple[RuntimeSafetyTransition, ...]:
        return tuple(self._history)

    def apply(
        self,
        evaluation: ProtectionEvaluation,
        *,
        recovery_approval: RecoveryApproval | None = None,
    ) -> SafetyUpdate:
        desired = evaluation.required_state
        current_rank = _STATE_RANK[self._state]
        desired_rank = _STATE_RANK[desired]
        transition: RuntimeSafetyTransition | None = None
        recovery_required = False

        if desired_rank > current_rank:
            transition = self._make_transition(
                desired,
                evaluation,
                TransitionTrigger.AUTOMATIC_ESCALATION,
                None,
            )
        elif desired_rank < current_rank:
            if recovery_approval is None:
                recovery_required = True
            else:
                if recovery_approval.target_state != desired:
                    raise RuntimeSafetyError("recovery approval target does not match evaluated safe state")
                if recovery_approval.approved_at < evaluation.evaluated_at:
                    raise RuntimeSafetyError("recovery approval must acknowledge the current evaluation")
                transition = self._make_transition(
                    desired,
                    evaluation,
                    TransitionTrigger.EXPLICIT_RECOVERY,
                    recovery_approval.approval_id,
                    changed_at=recovery_approval.approved_at,
                )
        if transition is not None:
            self._state = transition.to_state
            self._history.append(transition)
        return SafetyUpdate(
            state=self._state,
            transition=transition,
            recovery_required=recovery_required,
            required_state=desired,
            permissions=permissions_for(self._state),
        )

    def _make_transition(
        self,
        to_state: RuntimeSafetyState,
        evaluation: ProtectionEvaluation,
        trigger: TransitionTrigger,
        recovery_approval_id: str | None,
        *,
        changed_at: datetime | None = None,
    ) -> RuntimeSafetyTransition:
        at = changed_at or evaluation.evaluated_at
        body = {
            "from_state": self._state.value,
            "to_state": to_state.value,
            "changed_at": at.isoformat(),
            "trigger": trigger.value,
            "evaluation_hash": evaluation.evaluation_hash,
            "reason_codes": list(evaluation.reason_codes),
            "recovery_approval_id": recovery_approval_id,
        }
        transition_id = sha256(canonical_json(body).encode("utf-8")).hexdigest()
        return RuntimeSafetyTransition(
            transition_id=transition_id,
            from_state=self._state,
            to_state=to_state,
            changed_at=at,
            trigger=trigger,
            evaluation_hash=evaluation.evaluation_hash,
            reason_codes=evaluation.reason_codes,
            recovery_approval_id=recovery_approval_id,
        )


PROTECTION_EVALUATED_EVENT = "PROTECTION.EVALUATED"
RUNTIME_SAFETY_TRANSITION_EVENT = "RUNTIME_SAFETY.TRANSITION"


def protection_evaluated_event(evaluation: ProtectionEvaluation) -> DomainEvent:
    return DomainEvent.create(
        event_type=PROTECTION_EVALUATED_EVENT,
        aggregate_type="RUNTIME_SAFETY",
        aggregate_id="GLOBAL",
        occurred_at=evaluation.evaluated_at,
        correlation_id="RUNTIME_SAFETY",
        causation_id=None,
        producer="runtime_safety",
        schema_version=1,
        payload=evaluation.to_dict(),
    )


def runtime_safety_transition_event(
    transition: RuntimeSafetyTransition,
    *,
    causation_id: str,
) -> DomainEvent:
    return DomainEvent.create(
        event_type=RUNTIME_SAFETY_TRANSITION_EVENT,
        aggregate_type="RUNTIME_SAFETY",
        aggregate_id="GLOBAL",
        occurred_at=transition.changed_at,
        correlation_id="RUNTIME_SAFETY",
        causation_id=causation_id,
        producer="runtime_safety",
        schema_version=1,
        payload=transition.to_dict(),
    )


class RuntimeSafetyReplayState:
    def __init__(self) -> None:
        self.state = RuntimeSafetyState.ACTIVE
        self.transition_ids: list[str] = []


class RuntimeSafetyProjector:
    def initial_state(self) -> RuntimeSafetyReplayState:
        return RuntimeSafetyReplayState()

    def apply(self, state: RuntimeSafetyReplayState, event: DomainEvent) -> RuntimeSafetyReplayState:
        if event.event_type != RUNTIME_SAFETY_TRANSITION_EVENT:
            return state
        if event.aggregate_type != "RUNTIME_SAFETY" or event.aggregate_id != "GLOBAL":
            raise RuntimeSafetyError("runtime safety transition event has invalid aggregate")
        payload: Mapping[str, Any] = event.payload
        from_state = RuntimeSafetyState(str(payload["from_state"]))
        to_state = RuntimeSafetyState(str(payload["to_state"]))
        trigger = TransitionTrigger(str(payload["trigger"]))
        approval = payload.get("recovery_approval_id")
        transition = RuntimeSafetyTransition(
            transition_id=str(payload["transition_id"]),
            from_state=from_state,
            to_state=to_state,
            changed_at=datetime.fromisoformat(str(payload["changed_at"])),
            trigger=trigger,
            evaluation_hash=str(payload["evaluation_hash"]),
            reason_codes=tuple(str(item) for item in payload.get("reason_codes", [])),
            recovery_approval_id=None if approval is None else str(approval),
        )
        expected_body = {
            "from_state": transition.from_state.value,
            "to_state": transition.to_state.value,
            "changed_at": transition.changed_at.isoformat(),
            "trigger": transition.trigger.value,
            "evaluation_hash": transition.evaluation_hash,
            "reason_codes": list(transition.reason_codes),
            "recovery_approval_id": transition.recovery_approval_id,
        }
        expected_id = sha256(canonical_json(expected_body).encode("utf-8")).hexdigest()
        if expected_id != transition.transition_id:
            raise RuntimeSafetyError("runtime safety transition ID does not match content")
        if transition.from_state != state.state:
            raise RuntimeSafetyError("runtime safety replay state discontinuity")
        state.state = transition.to_state
        state.transition_ids.append(transition.transition_id)
        return state

    def snapshot(self, state: RuntimeSafetyReplayState) -> dict[str, Any]:
        return {
            "projection": "RUNTIME_SAFETY_V1",
            "state": state.state.value,
            "permissions": permissions_for(state.state).to_dict(),
            "transition_ids": list(state.transition_ids),
        }

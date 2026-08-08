"""Canonical TradeLead and Watchlist domain model for Phase 02B.

The lead is a decision-time research artifact.  Signal score, factor values,
strategy version, decision-time symbol, and data provenance are frozen.  Later
portfolio/risk/execution work may advance lifecycle state and attach a proposed
allocation, but cannot rewrite the research decision that produced the lead.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping
from uuid import UUID

from trading_bot.data.time_utils import require_aware


class LeadContractError(ValueError):
    """Raised when a TradeLead violates its deterministic domain contract."""


class LeadConflictError(LeadContractError):
    """Raised when two versions of the same lead contain conflicting history."""


class LeadDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class LeadLifecycleState(str, Enum):
    DISCOVERED = "DISCOVERED"
    WATCHLIST = "WATCHLIST"
    QUALIFIED = "QUALIFIED"
    RISK_REJECTED = "RISK_REJECTED"
    EVENT_BLOCKED = "EVENT_BLOCKED"
    COST_BLOCKED = "COST_BLOCKED"
    BORROW_BLOCKED = "BORROW_BLOCKED"
    PORTFOLIO_REJECTED = "PORTFOLIO_REJECTED"
    PLANNED = "PLANNED"
    ENTERED = "ENTERED"
    EXIT_PENDING = "EXIT_PENDING"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class LeadTrendState(str, Enum):
    ABOVE_SMA200 = "ABOVE_SMA200"
    BELOW_SMA200 = "BELOW_SMA200"
    AT_SMA200 = "AT_SMA200"
    UNKNOWN = "UNKNOWN"


class LeadVolatilityState(str, Enum):
    WITHIN_LIMIT = "WITHIN_LIMIT"
    ABOVE_LIMIT = "ABOVE_LIMIT"
    UNKNOWN = "UNKNOWN"


class LeadUniverseState(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


class EarningsState(str, Enum):
    CLEAR = "CLEAR"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class CostState(str, Enum):
    CLEAR = "CLEAR"
    BLOCKED = "BLOCKED"
    UNCALIBRATED = "UNCALIBRATED"
    UNKNOWN = "UNKNOWN"


class BorrowState(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class LeadReasonCode(str, Enum):
    SCORE_THRESHOLD_NOT_MET = "SCORE_THRESHOLD_NOT_MET"
    MOMENTUM_RULE_NOT_MET = "MOMENTUM_RULE_NOT_MET"
    TREND_RULE_NOT_MET = "TREND_RULE_NOT_MET"
    UNIVERSE_INELIGIBLE = "UNIVERSE_INELIGIBLE"
    CROSS_SECTION_INVALID = "CROSS_SECTION_INVALID"
    DATA_QUALITY_BLOCK = "DATA_QUALITY_BLOCK"
    EARNINGS_WINDOW = "EARNINGS_WINDOW"
    EVENT_UNRESOLVED = "EVENT_UNRESOLVED"
    SPREAD_TOO_WIDE = "SPREAD_TOO_WIDE"
    COST_ESTIMATE_UNAVAILABLE = "COST_ESTIMATE_UNAVAILABLE"
    BORROW_UNAVAILABLE = "BORROW_UNAVAILABLE"
    BORROW_COST_TOO_HIGH = "BORROW_COST_TOO_HIGH"
    BORROW_UNKNOWN = "BORROW_UNKNOWN"
    RISK_LIMIT = "RISK_LIMIT"
    PORTFOLIO_CAPACITY = "PORTFOLIO_CAPACITY"
    SECTOR_CAP = "SECTOR_CAP"
    CORRELATION_LIMIT = "CORRELATION_LIMIT"
    WHOLE_SHARE_INFEASIBLE = "WHOLE_SHARE_INFEASIBLE"
    MARKET_STRESS = "MARKET_STRESS"
    PROVENANCE_INCOMPLETE = "PROVENANCE_INCOMPLETE"
    FUTURE_DATA = "FUTURE_DATA"
    EXPIRED = "EXPIRED"
    OTHER = "OTHER"


_REASON_ACTIONS: dict[LeadReasonCode, str] = {
    LeadReasonCode.SCORE_THRESHOLD_NOT_MET: (
        "Await a future decision cycle whose frozen score meets the strategy threshold."
    ),
    LeadReasonCode.MOMENTUM_RULE_NOT_MET: (
        "Await a future decision cycle whose momentum signs satisfy the frozen strategy rule."
    ),
    LeadReasonCode.TREND_RULE_NOT_MET: (
        "Await a future decision cycle whose trend state satisfies the frozen strategy rule."
    ),
    LeadReasonCode.UNIVERSE_INELIGIBLE: "Instrument must become eligible at a future universe refresh.",
    LeadReasonCode.CROSS_SECTION_INVALID: "Wait for a valid cross-section at a future decision cycle.",
    LeadReasonCode.DATA_QUALITY_BLOCK: "Resolve the data-quality failure and recompute a new decision artifact.",
    LeadReasonCode.EARNINGS_WINDOW: "Wait until the approved earnings/event exclusion window clears.",
    LeadReasonCode.EVENT_UNRESOLVED: "Resolve the event state before qualification or planning.",
    LeadReasonCode.SPREAD_TOO_WIDE: "Spread must fall within the approved maximum at the next valid check.",
    LeadReasonCode.COST_ESTIMATE_UNAVAILABLE: "Obtain an approved point-in-time cost estimate.",
    LeadReasonCode.BORROW_UNAVAILABLE: "Approved borrow availability must become AVAILABLE.",
    LeadReasonCode.BORROW_COST_TOO_HIGH: "Borrow cost must fall within the approved limit.",
    LeadReasonCode.BORROW_UNKNOWN: "Obtain approved point-in-time borrow evidence.",
    LeadReasonCode.RISK_LIMIT: "Portfolio/risk constraints must clear before planning new exposure.",
    LeadReasonCode.PORTFOLIO_CAPACITY: "Portfolio capacity must become available.",
    LeadReasonCode.SECTOR_CAP: "Sector concentration must fall within the approved cap.",
    LeadReasonCode.CORRELATION_LIMIT: "Portfolio correlation constraint must clear.",
    LeadReasonCode.WHOLE_SHARE_INFEASIBLE: "Whole-share sizing must become feasible at a future planning check.",
    LeadReasonCode.MARKET_STRESS: "Market-stress block must clear before new risk is planned.",
    LeadReasonCode.PROVENANCE_INCOMPLETE: "Complete and validate all required provenance before use.",
    LeadReasonCode.FUTURE_DATA: "Rebuild the decision using only information available at decision time.",
    LeadReasonCode.EXPIRED: "Generate a new lead from a new decision cycle.",
    LeadReasonCode.OTHER: "Review the explicit blocking detail before qualification.",
}

_EVENT_CODES = {LeadReasonCode.EARNINGS_WINDOW, LeadReasonCode.EVENT_UNRESOLVED}
_COST_CODES = {LeadReasonCode.SPREAD_TOO_WIDE, LeadReasonCode.COST_ESTIMATE_UNAVAILABLE}
_BORROW_CODES = {
    LeadReasonCode.BORROW_UNAVAILABLE,
    LeadReasonCode.BORROW_COST_TOO_HIGH,
    LeadReasonCode.BORROW_UNKNOWN,
}
_RISK_CODES = {LeadReasonCode.RISK_LIMIT, LeadReasonCode.MARKET_STRESS}
_PORTFOLIO_CODES = {
    LeadReasonCode.PORTFOLIO_CAPACITY,
    LeadReasonCode.SECTOR_CAP,
    LeadReasonCode.CORRELATION_LIMIT,
    LeadReasonCode.WHOLE_SHARE_INFEASIBLE,
}

_PRE_ENTRY_STATES = {
    LeadLifecycleState.DISCOVERED,
    LeadLifecycleState.WATCHLIST,
    LeadLifecycleState.QUALIFIED,
    LeadLifecycleState.RISK_REJECTED,
    LeadLifecycleState.EVENT_BLOCKED,
    LeadLifecycleState.COST_BLOCKED,
    LeadLifecycleState.BORROW_BLOCKED,
    LeadLifecycleState.PORTFOLIO_REJECTED,
    LeadLifecycleState.PLANNED,
}

_WATCHLIST_STATES = {
    LeadLifecycleState.DISCOVERED,
    LeadLifecycleState.WATCHLIST,
    LeadLifecycleState.RISK_REJECTED,
    LeadLifecycleState.EVENT_BLOCKED,
    LeadLifecycleState.COST_BLOCKED,
    LeadLifecycleState.BORROW_BLOCKED,
    LeadLifecycleState.PORTFOLIO_REJECTED,
}

_ALLOWED_TRANSITIONS: dict[LeadLifecycleState, frozenset[LeadLifecycleState]] = {
    LeadLifecycleState.DISCOVERED: frozenset(
        {
            LeadLifecycleState.WATCHLIST,
            LeadLifecycleState.QUALIFIED,
            LeadLifecycleState.EVENT_BLOCKED,
            LeadLifecycleState.COST_BLOCKED,
            LeadLifecycleState.BORROW_BLOCKED,
            LeadLifecycleState.EXPIRED,
        }
    ),
    LeadLifecycleState.WATCHLIST: frozenset({LeadLifecycleState.EXPIRED}),
    LeadLifecycleState.QUALIFIED: frozenset(
        {
            LeadLifecycleState.RISK_REJECTED,
            LeadLifecycleState.EVENT_BLOCKED,
            LeadLifecycleState.COST_BLOCKED,
            LeadLifecycleState.BORROW_BLOCKED,
            LeadLifecycleState.PORTFOLIO_REJECTED,
            LeadLifecycleState.PLANNED,
            LeadLifecycleState.EXPIRED,
        }
    ),
    LeadLifecycleState.RISK_REJECTED: frozenset({LeadLifecycleState.EXPIRED}),
    LeadLifecycleState.EVENT_BLOCKED: frozenset({LeadLifecycleState.EXPIRED}),
    LeadLifecycleState.COST_BLOCKED: frozenset({LeadLifecycleState.EXPIRED}),
    LeadLifecycleState.BORROW_BLOCKED: frozenset({LeadLifecycleState.EXPIRED}),
    LeadLifecycleState.PORTFOLIO_REJECTED: frozenset({LeadLifecycleState.EXPIRED}),
    LeadLifecycleState.PLANNED: frozenset(
        {
            LeadLifecycleState.ENTERED,
            LeadLifecycleState.RISK_REJECTED,
            LeadLifecycleState.EVENT_BLOCKED,
            LeadLifecycleState.COST_BLOCKED,
            LeadLifecycleState.BORROW_BLOCKED,
            LeadLifecycleState.PORTFOLIO_REJECTED,
            LeadLifecycleState.EXPIRED,
        }
    ),
    LeadLifecycleState.ENTERED: frozenset({LeadLifecycleState.EXIT_PENDING}),
    LeadLifecycleState.EXIT_PENDING: frozenset({LeadLifecycleState.CLOSED}),
    LeadLifecycleState.CLOSED: frozenset(),
    LeadLifecycleState.EXPIRED: frozenset(),
}


def _decimal(value: Decimal | str | int | float, field_name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise LeadContractError(f"{field_name} must be numeric") from exc
    if not result.is_finite():
        raise LeadContractError(f"{field_name} must be finite")
    return result


def _sha256_hex(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise LeadContractError(f"{field_name} must be a 64-character SHA-256 hex digest")
    return normalized


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class FactorObservation:
    name: str
    value: Decimal
    available_at: datetime

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise LeadContractError("factor name is required")
        object.__setattr__(self, "value", _decimal(self.value, f"factor[{self.name}].value"))
        object.__setattr__(
            self, "available_at", require_aware(self.available_at, f"factor[{self.name}].available_at")
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "value": str(self.value),
            "available_at": self.available_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FactorObservation":
        return cls(
            name=str(payload["name"]),
            value=Decimal(str(payload["value"])),
            available_at=datetime.fromisoformat(str(payload["available_at"])),
        )


@dataclass(frozen=True, slots=True)
class LeadProvenance:
    dataset_manifest_hash: str
    universe_manifest_hash: str
    feature_manifest_hash: str
    max_input_available_at: datetime
    source_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dataset_manifest_hash",
            _sha256_hex(self.dataset_manifest_hash, "dataset_manifest_hash"),
        )
        object.__setattr__(
            self,
            "universe_manifest_hash",
            _sha256_hex(self.universe_manifest_hash, "universe_manifest_hash"),
        )
        object.__setattr__(
            self,
            "feature_manifest_hash",
            _sha256_hex(self.feature_manifest_hash, "feature_manifest_hash"),
        )
        object.__setattr__(
            self,
            "max_input_available_at",
            require_aware(self.max_input_available_at, "max_input_available_at"),
        )
        if any(not item.strip() for item in self.source_event_ids):
            raise LeadContractError("source_event_ids cannot contain blanks")
        if len(self.source_event_ids) != len(set(self.source_event_ids)):
            raise LeadContractError("source_event_ids cannot contain duplicates")
        object.__setattr__(self, "source_event_ids", tuple(sorted(self.source_event_ids)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_manifest_hash": self.dataset_manifest_hash,
            "universe_manifest_hash": self.universe_manifest_hash,
            "feature_manifest_hash": self.feature_manifest_hash,
            "max_input_available_at": self.max_input_available_at.isoformat(),
            "source_event_ids": list(self.source_event_ids),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LeadProvenance":
        return cls(
            dataset_manifest_hash=str(payload["dataset_manifest_hash"]),
            universe_manifest_hash=str(payload["universe_manifest_hash"]),
            feature_manifest_hash=str(payload["feature_manifest_hash"]),
            max_input_available_at=datetime.fromisoformat(str(payload["max_input_available_at"])),
            source_event_ids=tuple(str(item) for item in payload.get("source_event_ids", ())),
        )


@dataclass(frozen=True, slots=True)
class LeadReason:
    code: LeadReasonCode
    detail: str
    available_at: datetime
    blocking: bool = True

    def __post_init__(self) -> None:
        if not self.detail.strip():
            raise LeadContractError("lead reason detail is required")
        object.__setattr__(self, "available_at", require_aware(self.available_at, "reason.available_at"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "detail": self.detail,
            "available_at": self.available_at.isoformat(),
            "blocking": self.blocking,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LeadReason":
        return cls(
            code=LeadReasonCode(str(payload["code"])),
            detail=str(payload["detail"]),
            available_at=datetime.fromisoformat(str(payload["available_at"])),
            blocking=bool(payload.get("blocking", True)),
        )


@dataclass(frozen=True, slots=True)
class LeadTransition:
    transition_id: str
    from_state: LeadLifecycleState | None
    to_state: LeadLifecycleState
    changed_at: datetime
    reason_codes: tuple[LeadReasonCode, ...] = ()

    def __post_init__(self) -> None:
        if not self.transition_id.strip():
            raise LeadContractError("transition_id is required")
        object.__setattr__(self, "changed_at", require_aware(self.changed_at, "transition.changed_at"))
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise LeadContractError("transition reason_codes cannot contain duplicates")

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_state": None if self.from_state is None else self.from_state.value,
            "to_state": self.to_state.value,
            "changed_at": self.changed_at.isoformat(),
            "reason_codes": [item.value for item in self.reason_codes],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LeadTransition":
        raw_from = payload.get("from_state")
        return cls(
            transition_id=str(payload["transition_id"]),
            from_state=None if raw_from is None else LeadLifecycleState(str(raw_from)),
            to_state=LeadLifecycleState(str(payload["to_state"])),
            changed_at=datetime.fromisoformat(str(payload["changed_at"])),
            reason_codes=tuple(LeadReasonCode(str(item)) for item in payload.get("reason_codes", ())),
        )


def _lead_id_payload(
    *,
    instrument_id: UUID,
    strategy_id: str,
    strategy_version: str,
    decision_at: datetime,
    direction: LeadDirection,
    provenance: LeadProvenance,
) -> dict[str, str]:
    return {
        "instrument_id": str(instrument_id),
        "strategy_id": strategy_id,
        "strategy_version": strategy_version,
        "decision_at": decision_at.isoformat(),
        "direction": direction.value,
        "dataset_manifest_hash": provenance.dataset_manifest_hash,
        "universe_manifest_hash": provenance.universe_manifest_hash,
        "feature_manifest_hash": provenance.feature_manifest_hash,
    }


def _lead_id(**kwargs: Any) -> str:
    return f"lead_{_stable_hash(_lead_id_payload(**kwargs))}"


def _transition_id(
    lead_id: str,
    from_state: LeadLifecycleState | None,
    to_state: LeadLifecycleState,
    changed_at: datetime,
    reason_codes: tuple[LeadReasonCode, ...],
) -> str:
    payload = {
        "lead_id": lead_id,
        "from_state": None if from_state is None else from_state.value,
        "to_state": to_state.value,
        "changed_at": changed_at.isoformat(),
        "reason_codes": [item.value for item in reason_codes],
    }
    return f"transition_{_stable_hash(payload)}"


def _required_reason_codes_for_state(state: LeadLifecycleState) -> set[LeadReasonCode] | None:
    if state == LeadLifecycleState.EVENT_BLOCKED:
        return _EVENT_CODES
    if state == LeadLifecycleState.COST_BLOCKED:
        return _COST_CODES
    if state == LeadLifecycleState.BORROW_BLOCKED:
        return _BORROW_CODES
    if state == LeadLifecycleState.RISK_REJECTED:
        return _RISK_CODES
    if state == LeadLifecycleState.PORTFOLIO_REJECTED:
        return _PORTFOLIO_CODES
    if state == LeadLifecycleState.WATCHLIST:
        return set(LeadReasonCode) - {LeadReasonCode.EXPIRED}
    if state == LeadLifecycleState.EXPIRED:
        return {LeadReasonCode.EXPIRED}
    return None


def _validate_state_reasons(state: LeadLifecycleState, reasons: tuple[LeadReason, ...]) -> None:
    blocking_codes = {reason.code for reason in reasons if reason.blocking}
    required = _required_reason_codes_for_state(state)
    if required is not None and not (blocking_codes & required):
        raise LeadContractError(f"{state.value} requires a matching blocking reason code")
    if state in {
        LeadLifecycleState.QUALIFIED,
        LeadLifecycleState.PLANNED,
        LeadLifecycleState.ENTERED,
        LeadLifecycleState.EXIT_PENDING,
        LeadLifecycleState.CLOSED,
    } and blocking_codes:
        raise LeadContractError(f"{state.value} cannot carry active blocking reasons")


@dataclass(frozen=True, slots=True)
class TradeLead:
    lead_id: str
    instrument_id: UUID
    decision_symbol: str
    decision_symbol_available_at: datetime
    display_symbol: str
    display_symbol_as_of: datetime
    strategy_id: str
    strategy_version: str
    generated_at: datetime
    decision_at: datetime
    valid_until: datetime
    direction: LeadDirection
    score: Decimal
    factors: tuple[FactorObservation, ...]
    trend_state: LeadTrendState
    volatility_state: LeadVolatilityState
    universe_state: LeadUniverseState
    earnings_state: EarningsState
    cost_state: CostState
    borrow_state: BorrowState
    provenance: LeadProvenance
    state: LeadLifecycleState
    active_reasons: tuple[LeadReason, ...] = ()
    transition_history: tuple[LeadTransition, ...] = ()
    estimated_spread_bps: Decimal | None = None
    estimated_cost_bps: Decimal | None = None
    proposed_weight: Decimal | None = None
    proposed_shares: int | None = None

    def __post_init__(self) -> None:
        for name in ("decision_symbol", "display_symbol", "strategy_id", "strategy_version"):
            if not str(getattr(self, name)).strip():
                raise LeadContractError(f"{name} is required")
        decision_at = require_aware(self.decision_at, "decision_at")
        generated_at = require_aware(self.generated_at, "generated_at")
        valid_until = require_aware(self.valid_until, "valid_until")
        decision_symbol_available_at = require_aware(
            self.decision_symbol_available_at, "decision_symbol_available_at"
        )
        display_symbol_as_of = require_aware(self.display_symbol_as_of, "display_symbol_as_of")
        object.__setattr__(self, "decision_at", decision_at)
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "valid_until", valid_until)
        object.__setattr__(self, "decision_symbol_available_at", decision_symbol_available_at)
        object.__setattr__(self, "display_symbol_as_of", display_symbol_as_of)
        object.__setattr__(self, "score", _decimal(self.score, "score"))

        if generated_at < decision_at:
            raise LeadContractError("generated_at cannot precede decision_at")
        if valid_until <= decision_at or generated_at > valid_until:
            raise LeadContractError("valid_until must be later than decision_at and generation")
        if decision_symbol_available_at > decision_at:
            raise LeadContractError("decision symbol cannot use future information")
        if self.provenance.max_input_available_at > decision_at:
            raise LeadContractError("lead provenance contains information unavailable at decision time")

        factor_names = [factor.name for factor in self.factors]
        if len(factor_names) != len(set(factor_names)):
            raise LeadContractError("factor names must be unique")
        if tuple(sorted(factor_names)) != tuple(factor_names):
            raise LeadContractError("factors must be stored in deterministic name order")
        if any(factor.available_at > decision_at for factor in self.factors):
            raise LeadContractError("lead factor contains future information")

        for reason in self.active_reasons:
            if reason.available_at > max(generated_at, self.transition_history[-1].changed_at if self.transition_history else generated_at):
                raise LeadContractError("active reason cannot be known after the current lead state")
        if len({(reason.code, reason.detail, reason.available_at, reason.blocking) for reason in self.active_reasons}) != len(self.active_reasons):
            raise LeadContractError("active reasons cannot contain duplicates")

        if self.estimated_spread_bps is not None:
            spread = _decimal(self.estimated_spread_bps, "estimated_spread_bps")
            if spread < 0:
                raise LeadContractError("estimated_spread_bps cannot be negative")
            object.__setattr__(self, "estimated_spread_bps", spread)
        if self.estimated_cost_bps is not None:
            cost = _decimal(self.estimated_cost_bps, "estimated_cost_bps")
            if cost < 0:
                raise LeadContractError("estimated_cost_bps cannot be negative")
            object.__setattr__(self, "estimated_cost_bps", cost)

        if self.proposed_weight is not None:
            weight = _decimal(self.proposed_weight, "proposed_weight")
            if abs(weight) > 1:
                raise LeadContractError("proposed_weight absolute value cannot exceed 1")
            if self.direction == LeadDirection.LONG and weight < 0:
                raise LeadContractError("LONG lead proposed_weight cannot be negative")
            if self.direction == LeadDirection.SHORT and weight > 0:
                raise LeadContractError("SHORT lead proposed_weight cannot be positive")
            object.__setattr__(self, "proposed_weight", weight)
        if self.proposed_shares is not None:
            if isinstance(self.proposed_shares, bool) or not isinstance(self.proposed_shares, int):
                raise LeadContractError("proposed_shares must be an integer")
            if self.proposed_shares <= 0:
                raise LeadContractError("proposed_shares must be positive when supplied")

        if self.direction == LeadDirection.LONG and self.borrow_state != BorrowState.NOT_APPLICABLE:
            raise LeadContractError("LONG leads must use borrow_state=NOT_APPLICABLE")
        if self.direction == LeadDirection.SHORT and self.borrow_state == BorrowState.NOT_APPLICABLE:
            raise LeadContractError("SHORT leads require an explicit borrow state")
        if self.state == LeadLifecycleState.BORROW_BLOCKED and self.direction != LeadDirection.SHORT:
            raise LeadContractError("BORROW_BLOCKED is only valid for SHORT leads")

        if self.state in {
            LeadLifecycleState.PLANNED,
            LeadLifecycleState.ENTERED,
            LeadLifecycleState.EXIT_PENDING,
            LeadLifecycleState.CLOSED,
        } and (self.proposed_weight is None or self.proposed_shares is None):
            raise LeadContractError(f"{self.state.value} requires a proposed allocation")

        if self.state in {
            LeadLifecycleState.QUALIFIED,
            LeadLifecycleState.PLANNED,
            LeadLifecycleState.ENTERED,
        }:
            if self.universe_state != LeadUniverseState.ELIGIBLE:
                raise LeadContractError(f"{self.state.value} requires universe ELIGIBLE")
            if self.earnings_state != EarningsState.CLEAR:
                raise LeadContractError(f"{self.state.value} requires earnings CLEAR")
            if self.cost_state != CostState.CLEAR:
                raise LeadContractError(f"{self.state.value} requires cost CLEAR")
            if self.direction == LeadDirection.SHORT and self.borrow_state != BorrowState.AVAILABLE:
                raise LeadContractError(f"{self.state.value} SHORT lead requires borrow AVAILABLE")

        expected_id = _lead_id(
            instrument_id=self.instrument_id,
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            decision_at=decision_at,
            direction=self.direction,
            provenance=self.provenance,
        )
        if self.lead_id != expected_id:
            raise LeadContractError("lead_id does not match deterministic decision identity")

        self._validate_history()
        _validate_state_reasons(self.state, self.active_reasons)

    def _validate_history(self) -> None:
        if not self.transition_history:
            raise LeadContractError("transition_history is required")
        first = self.transition_history[0]
        if first.from_state is not None or first.to_state != LeadLifecycleState.DISCOVERED:
            raise LeadContractError("transition history must start with creation into DISCOVERED")
        if first.changed_at != self.generated_at:
            raise LeadContractError("creation transition must occur at generated_at")
        previous_state: LeadLifecycleState | None = None
        previous_time: datetime | None = None
        seen_ids: set[str] = set()
        for transition in self.transition_history:
            if transition.transition_id in seen_ids:
                raise LeadContractError("duplicate transition_id")
            seen_ids.add(transition.transition_id)
            expected_transition_id = _transition_id(
                self.lead_id,
                transition.from_state,
                transition.to_state,
                transition.changed_at,
                transition.reason_codes,
            )
            if transition.transition_id != expected_transition_id:
                raise LeadContractError("transition_id does not match transition contents")
            if transition.from_state != previous_state:
                raise LeadContractError("transition history contains a broken state chain")
            if previous_time is not None and transition.changed_at < previous_time:
                raise LeadContractError("transition history cannot move backward in time")
            if previous_state is not None and transition.to_state not in _ALLOWED_TRANSITIONS[previous_state]:
                raise LeadContractError(
                    f"invalid lifecycle transition {previous_state.value}->{transition.to_state.value}"
                )
            previous_state = transition.to_state
            previous_time = transition.changed_at
        if previous_state != self.state:
            raise LeadContractError("transition history does not end at current state")

    @classmethod
    def create(
        cls,
        *,
        instrument_id: UUID,
        decision_symbol: str,
        decision_symbol_available_at: datetime,
        display_symbol: str,
        display_symbol_as_of: datetime,
        strategy_id: str,
        strategy_version: str,
        generated_at: datetime,
        decision_at: datetime,
        valid_until: datetime,
        direction: LeadDirection,
        score: Decimal | str | int | float,
        factors: Iterable[FactorObservation],
        trend_state: LeadTrendState,
        volatility_state: LeadVolatilityState,
        universe_state: LeadUniverseState,
        earnings_state: EarningsState,
        cost_state: CostState,
        borrow_state: BorrowState,
        provenance: LeadProvenance,
        initial_state: LeadLifecycleState = LeadLifecycleState.DISCOVERED,
        reasons: Iterable[LeadReason] = (),
        estimated_spread_bps: Decimal | str | int | float | None = None,
        estimated_cost_bps: Decimal | str | int | float | None = None,
    ) -> "TradeLead":
        decision_at_utc = require_aware(decision_at, "decision_at")
        generated_at_utc = require_aware(generated_at, "generated_at")
        lead_id = _lead_id(
            instrument_id=instrument_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            decision_at=decision_at_utc,
            direction=direction,
            provenance=provenance,
        )
        creation = LeadTransition(
            transition_id=_transition_id(
                lead_id,
                None,
                LeadLifecycleState.DISCOVERED,
                generated_at_utc,
                (),
            ),
            from_state=None,
            to_state=LeadLifecycleState.DISCOVERED,
            changed_at=generated_at_utc,
            reason_codes=(),
        )
        history: tuple[LeadTransition, ...] = (creation,)
        state = LeadLifecycleState.DISCOVERED
        reason_tuple = tuple(sorted(
            reasons,
            key=lambda reason: (reason.code.value, reason.detail, reason.available_at, reason.blocking),
        ))
        if any(reason.available_at > decision_at_utc for reason in reason_tuple):
            raise LeadContractError("initial lead reasons must be known by decision_at")
        if initial_state != LeadLifecycleState.DISCOVERED:
            if initial_state not in _ALLOWED_TRANSITIONS[LeadLifecycleState.DISCOVERED]:
                raise LeadContractError(f"invalid initial lead state {initial_state.value}")
            reason_codes = tuple(sorted({reason.code for reason in reason_tuple}, key=lambda item: item.value))
            initial_transition = LeadTransition(
                transition_id=_transition_id(
                    lead_id,
                    LeadLifecycleState.DISCOVERED,
                    initial_state,
                    generated_at_utc,
                    reason_codes,
                ),
                from_state=LeadLifecycleState.DISCOVERED,
                to_state=initial_state,
                changed_at=generated_at_utc,
                reason_codes=reason_codes,
            )
            history += (initial_transition,)
            state = initial_state
        return cls(
            lead_id=lead_id,
            instrument_id=instrument_id,
            decision_symbol=decision_symbol,
            decision_symbol_available_at=decision_symbol_available_at,
            display_symbol=display_symbol,
            display_symbol_as_of=display_symbol_as_of,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            generated_at=generated_at_utc,
            decision_at=decision_at_utc,
            valid_until=valid_until,
            direction=direction,
            score=_decimal(score, "score"),
            factors=tuple(sorted(factors, key=lambda factor: factor.name)),
            trend_state=trend_state,
            volatility_state=volatility_state,
            universe_state=universe_state,
            earnings_state=earnings_state,
            cost_state=cost_state,
            borrow_state=borrow_state,
            provenance=provenance,
            state=state,
            active_reasons=reason_tuple,
            transition_history=history,
            estimated_spread_bps=None if estimated_spread_bps is None else _decimal(estimated_spread_bps, "estimated_spread_bps"),
            estimated_cost_bps=None if estimated_cost_bps is None else _decimal(estimated_cost_bps, "estimated_cost_bps"),
        )

    def transition(
        self,
        to_state: LeadLifecycleState,
        *,
        changed_at: datetime,
        reasons: Iterable[LeadReason] = (),
    ) -> "TradeLead":
        changed = require_aware(changed_at, "changed_at")
        reason_tuple = tuple(sorted(
            reasons,
            key=lambda reason: (reason.code.value, reason.detail, reason.available_at, reason.blocking),
        ))
        reason_codes = tuple(sorted({reason.code for reason in reason_tuple}, key=lambda item: item.value))

        if to_state == self.state:
            last = self.transition_history[-1]
            candidate_id = _transition_id(self.lead_id, last.from_state, to_state, changed, reason_codes)
            if last.transition_id == candidate_id and reason_tuple == self.active_reasons:
                return self
            raise LeadContractError("same-state transition is not a valid lifecycle change")

        if to_state not in _ALLOWED_TRANSITIONS[self.state]:
            raise LeadContractError(f"invalid lifecycle transition {self.state.value}->{to_state.value}")
        if changed < self.transition_history[-1].changed_at:
            raise LeadContractError("transition cannot move backward in time")
        if any(reason.available_at > changed for reason in reason_tuple):
            raise LeadContractError("transition cannot use a reason that was not yet available")
        if self.state in _PRE_ENTRY_STATES and to_state != LeadLifecycleState.EXPIRED and changed > self.valid_until:
            raise LeadContractError("pre-entry transition cannot occur after lead validity expired")
        if to_state == LeadLifecycleState.EXPIRED and changed < self.valid_until:
            raise LeadContractError("lead cannot expire before valid_until")

        _validate_state_reasons(to_state, reason_tuple)
        transition = LeadTransition(
            transition_id=_transition_id(self.lead_id, self.state, to_state, changed, reason_codes),
            from_state=self.state,
            to_state=to_state,
            changed_at=changed,
            reason_codes=reason_codes,
        )
        return replace(
            self,
            state=to_state,
            active_reasons=reason_tuple,
            transition_history=self.transition_history + (transition,),
        )

    def with_allocation(
        self,
        *,
        proposed_weight: Decimal | str | int | float,
        proposed_shares: int,
    ) -> "TradeLead":
        if self.state not in {LeadLifecycleState.QUALIFIED, LeadLifecycleState.PLANNED}:
            raise LeadContractError("allocation can only be attached to QUALIFIED or PLANNED leads")
        weight = _decimal(proposed_weight, "proposed_weight")
        if self.proposed_weight is not None or self.proposed_shares is not None:
            if self.proposed_weight == weight and self.proposed_shares == proposed_shares:
                return self
            raise LeadConflictError("lead allocation is immutable once assigned")
        return replace(self, proposed_weight=weight, proposed_shares=proposed_shares)

    def with_display_symbol(self, *, display_symbol: str, as_of: datetime) -> "TradeLead":
        as_of_utc = require_aware(as_of, "display_symbol_as_of")
        if as_of_utc < self.display_symbol_as_of:
            raise LeadContractError("display symbol presentation cannot move backward in time")
        if not display_symbol.strip():
            raise LeadContractError("display_symbol is required")
        if display_symbol == self.display_symbol and as_of_utc == self.display_symbol_as_of:
            return self
        return replace(self, display_symbol=display_symbol, display_symbol_as_of=as_of_utc)

    @property
    def blocking_reasons(self) -> tuple[LeadReason, ...]:
        return tuple(reason for reason in self.active_reasons if reason.blocking)

    @property
    def immutable_fingerprint(self) -> str:
        payload = self.to_dict()
        for key in (
            "display_symbol",
            "display_symbol_as_of",
            "state",
            "active_reasons",
            "transition_history",
            "proposed_weight",
            "proposed_shares",
        ):
            payload.pop(key, None)
        return _stable_hash(payload)

    @property
    def content_hash(self) -> str:
        return _stable_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "instrument_id": str(self.instrument_id),
            "decision_symbol": self.decision_symbol,
            "decision_symbol_available_at": self.decision_symbol_available_at.isoformat(),
            "display_symbol": self.display_symbol,
            "display_symbol_as_of": self.display_symbol_as_of.isoformat(),
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "generated_at": self.generated_at.isoformat(),
            "decision_at": self.decision_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "direction": self.direction.value,
            "score": str(self.score),
            "factors": [factor.to_dict() for factor in self.factors],
            "trend_state": self.trend_state.value,
            "volatility_state": self.volatility_state.value,
            "universe_state": self.universe_state.value,
            "earnings_state": self.earnings_state.value,
            "cost_state": self.cost_state.value,
            "borrow_state": self.borrow_state.value,
            "provenance": self.provenance.to_dict(),
            "state": self.state.value,
            "active_reasons": [reason.to_dict() for reason in self.active_reasons],
            "transition_history": [transition.to_dict() for transition in self.transition_history],
            "estimated_spread_bps": None if self.estimated_spread_bps is None else str(self.estimated_spread_bps),
            "estimated_cost_bps": None if self.estimated_cost_bps is None else str(self.estimated_cost_bps),
            "proposed_weight": None if self.proposed_weight is None else str(self.proposed_weight),
            "proposed_shares": self.proposed_shares,
        }

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TradeLead":
        def optional_decimal(key: str) -> Decimal | None:
            value = payload.get(key)
            return None if value is None else Decimal(str(value))

        return cls(
            lead_id=str(payload["lead_id"]),
            instrument_id=UUID(str(payload["instrument_id"])),
            decision_symbol=str(payload["decision_symbol"]),
            decision_symbol_available_at=datetime.fromisoformat(str(payload["decision_symbol_available_at"])),
            display_symbol=str(payload["display_symbol"]),
            display_symbol_as_of=datetime.fromisoformat(str(payload["display_symbol_as_of"])),
            strategy_id=str(payload["strategy_id"]),
            strategy_version=str(payload["strategy_version"]),
            generated_at=datetime.fromisoformat(str(payload["generated_at"])),
            decision_at=datetime.fromisoformat(str(payload["decision_at"])),
            valid_until=datetime.fromisoformat(str(payload["valid_until"])),
            direction=LeadDirection(str(payload["direction"])),
            score=Decimal(str(payload["score"])),
            factors=tuple(FactorObservation.from_dict(item) for item in payload.get("factors", ())),
            trend_state=LeadTrendState(str(payload["trend_state"])),
            volatility_state=LeadVolatilityState(str(payload["volatility_state"])),
            universe_state=LeadUniverseState(str(payload["universe_state"])),
            earnings_state=EarningsState(str(payload["earnings_state"])),
            cost_state=CostState(str(payload["cost_state"])),
            borrow_state=BorrowState(str(payload["borrow_state"])),
            provenance=LeadProvenance.from_dict(payload["provenance"]),
            state=LeadLifecycleState(str(payload["state"])),
            active_reasons=tuple(LeadReason.from_dict(item) for item in payload.get("active_reasons", ())),
            transition_history=tuple(
                LeadTransition.from_dict(item) for item in payload.get("transition_history", ())
            ),
            estimated_spread_bps=optional_decimal("estimated_spread_bps"),
            estimated_cost_bps=optional_decimal("estimated_cost_bps"),
            proposed_weight=optional_decimal("proposed_weight"),
            proposed_shares=None if payload.get("proposed_shares") is None else int(payload["proposed_shares"]),
        )

    @classmethod
    def from_json(cls, raw: str) -> "TradeLead":
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise LeadContractError("serialized TradeLead must be a JSON object")
        return cls.from_dict(payload)


@dataclass(frozen=True, slots=True)
class WatchlistEntry:
    lead_id: str
    instrument_id: UUID
    symbol: str
    direction: LeadDirection
    state: LeadLifecycleState
    score: Decimal
    blocking_reasons: tuple[LeadReason, ...]
    qualification_actions: tuple[str, ...]
    valid_until: datetime
    lead_content_hash: str

    def __post_init__(self) -> None:
        if self.state not in _WATCHLIST_STATES:
            raise LeadContractError(f"{self.state.value} is not a watchlist-compatible lead state")
        object.__setattr__(self, "valid_until", require_aware(self.valid_until, "watchlist.valid_until"))
        if not self.blocking_reasons and self.state != LeadLifecycleState.DISCOVERED:
            raise LeadContractError("watchlist entries require explicit blocking reasons")

    def to_dict(self) -> dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "instrument_id": str(self.instrument_id),
            "symbol": self.symbol,
            "direction": self.direction.value,
            "state": self.state.value,
            "score": str(self.score),
            "blocking_reasons": [reason.to_dict() for reason in self.blocking_reasons],
            "qualification_actions": list(self.qualification_actions),
            "valid_until": self.valid_until.isoformat(),
            "lead_content_hash": self.lead_content_hash,
        }


def derive_watchlist_entry(lead: TradeLead) -> WatchlistEntry:
    if lead.state not in _WATCHLIST_STATES:
        raise LeadContractError(f"lead state {lead.state.value} does not belong on the watchlist")
    blockers = lead.blocking_reasons
    actions = tuple(dict.fromkeys(_REASON_ACTIONS[reason.code] for reason in blockers))
    return WatchlistEntry(
        lead_id=lead.lead_id,
        instrument_id=lead.instrument_id,
        symbol=lead.display_symbol,
        direction=lead.direction,
        state=lead.state,
        score=lead.score,
        blocking_reasons=blockers,
        qualification_actions=actions,
        valid_until=lead.valid_until,
        lead_content_hash=lead.content_hash,
    )


class TradeLeadBook:
    """Idempotent in-memory lead registry used by later API/event work.

    The book accepts duplicate snapshots, newer lifecycle-history extensions, and
    stale snapshots.  It rejects conflicting immutable research content or
    divergent lifecycle history for the same deterministic lead ID.
    """

    def __init__(self) -> None:
        self._leads: dict[str, TradeLead] = {}

    def ingest(self, lead: TradeLead) -> TradeLead:
        existing = self._leads.get(lead.lead_id)
        if existing is None:
            self._leads[lead.lead_id] = lead
            return lead
        if existing.immutable_fingerprint != lead.immutable_fingerprint:
            raise LeadConflictError("same lead_id has conflicting immutable research content")
        if existing.content_hash == lead.content_hash:
            return existing

        existing_history = existing.transition_history
        incoming_history = lead.transition_history
        shared = min(len(existing_history), len(incoming_history))
        if existing_history[:shared] != incoming_history[:shared]:
            raise LeadConflictError("same lead_id has divergent lifecycle history")

        if len(incoming_history) < len(existing_history):
            return existing

        if lead.display_symbol_as_of < existing.display_symbol_as_of:
            raise LeadConflictError("newer lead snapshot cannot regress display-symbol as-of time")
        if (
            lead.display_symbol_as_of == existing.display_symbol_as_of
            and lead.display_symbol != existing.display_symbol
        ):
            raise LeadConflictError("same as-of time has conflicting display symbols")
        if existing.proposed_weight is not None or existing.proposed_shares is not None:
            if (
                lead.proposed_weight != existing.proposed_weight
                or lead.proposed_shares != existing.proposed_shares
            ):
                raise LeadConflictError("newer lead snapshot cannot rewrite an assigned allocation")

        if len(incoming_history) > len(existing_history):
            self._leads[lead.lead_id] = lead
            return lead

        # Same lifecycle history may still have a presentation-symbol update or
        # a once-only portfolio allocation. Merge only when changes are monotonic.
        candidate = existing
        if lead.display_symbol_as_of > existing.display_symbol_as_of:
            candidate = candidate.with_display_symbol(
                display_symbol=lead.display_symbol, as_of=lead.display_symbol_as_of
            )
        elif (
            lead.display_symbol_as_of == existing.display_symbol_as_of
            and lead.display_symbol != existing.display_symbol
        ):
            raise LeadConflictError("same as-of time has conflicting display symbols")

        if lead.proposed_weight is not None or lead.proposed_shares is not None:
            if lead.proposed_weight is None or lead.proposed_shares is None:
                raise LeadConflictError("partial allocation is not valid")
            candidate = candidate.with_allocation(
                proposed_weight=lead.proposed_weight,
                proposed_shares=lead.proposed_shares,
            )
        if candidate.content_hash != lead.content_hash:
            raise LeadConflictError("same lead history has conflicting mutable projection")
        self._leads[lead.lead_id] = candidate
        return candidate

    def get(self, lead_id: str) -> TradeLead | None:
        return self._leads.get(lead_id)

    def all(self) -> tuple[TradeLead, ...]:
        return tuple(self._leads[key] for key in sorted(self._leads))

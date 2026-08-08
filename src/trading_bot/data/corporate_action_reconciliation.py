"""Provider-to-kernel corporate-action reconciliation.

This module never treats a provider-adjusted price as the source of truth. It
compares normalized event economics against the Phase 02 CorporateAction
contract and fails closed on missing, conflicting, or incomplete evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Iterable, Mapping

from .contracts import CorporateAction, CorporateActionStatus, CorporateActionType
from .errors import DataContractError
from .time_utils import require_aware

ZERO = Decimal("0")
ONE = Decimal("1")


class EvidenceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    DELETED = "DELETED"


class ReconciliationStatus(str, Enum):
    PASS = "PASS"
    MISMATCH = "MISMATCH"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ProviderCorporateActionEvidence:
    provider: str
    provider_event_id: str
    action_type: CorporateActionType
    effective_at: datetime
    available_at: datetime
    source_snapshot_id: str
    status: EvidenceStatus = EvidenceStatus.ACTIVE
    share_multiplier: Decimal | None = None
    cash_amount: Decimal | None = None
    currency: str | None = None
    stock_ratio: Decimal | None = None
    outturn_identifier: str | None = None
    revision: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.provider_event_id.strip():
            raise DataContractError("provider and provider_event_id are required")
        if not self.source_snapshot_id.strip():
            raise DataContractError("source_snapshot_id is required")
        object.__setattr__(self, "effective_at", require_aware(self.effective_at, "effective_at"))
        object.__setattr__(self, "available_at", require_aware(self.available_at, "available_at"))
        if self.revision < 0:
            raise DataContractError("revision cannot be negative")
        if self.share_multiplier is not None and self.share_multiplier <= ZERO:
            raise DataContractError("share_multiplier must be positive")
        if self.cash_amount is not None and self.cash_amount < ZERO:
            raise DataContractError("cash_amount cannot be negative")
        if self.stock_ratio is not None and self.stock_ratio < ZERO:
            raise DataContractError("stock_ratio cannot be negative")
        if self.cash_amount is not None and not self.currency:
            raise DataContractError("cash-bearing evidence requires currency")


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    action_id: str
    provider: str
    provider_event_id: str
    status: ReconciliationStatus
    reasons: tuple[str, ...]


def _close_decimal(left: Decimal | None, right: Decimal | None, tolerance: Decimal) -> bool:
    if left is None or right is None:
        return left is right
    return abs(left - right) <= tolerance


def _expected_share_multiplier(action: CorporateAction) -> Decimal | None:
    if action.action_type in {CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT}:
        assert action.split_new_shares is not None and action.split_old_shares is not None
        return action.split_new_shares / action.split_old_shares
    return None


def reconcile_corporate_action(
    action: CorporateAction,
    evidence: ProviderCorporateActionEvidence,
    *,
    expected_outturn_identifier: str | None = None,
    tolerance: Decimal = Decimal("0.000001"),
) -> ReconciliationResult:
    reasons: list[str] = []
    if evidence.status != EvidenceStatus.ACTIVE:
        reasons.append(f"provider evidence status is {evidence.status.value}")
    if action.status == CorporateActionStatus.CANCELLED:
        if evidence.status not in {EvidenceStatus.CANCELLED, EvidenceStatus.DELETED}:
            reasons.append("kernel action is cancelled but provider evidence remains active")
    elif action.action_type != evidence.action_type:
        reasons.append(f"action type mismatch: {action.action_type.value} != {evidence.action_type.value}")

    # Compare the economic session rather than exact timestamp because some vendors
    # publish an effective date without an exchange-local time.
    if action.effective_at.date() != evidence.effective_at.date():
        reasons.append("effective date mismatch")

    expected_multiplier = _expected_share_multiplier(action)
    if expected_multiplier is not None and not _close_decimal(expected_multiplier, evidence.share_multiplier, tolerance):
        reasons.append("share multiplier mismatch")

    if action.action_type == CorporateActionType.CASH_DIVIDEND:
        if not _close_decimal(action.cash_amount, evidence.cash_amount, tolerance):
            reasons.append("cash dividend amount mismatch")
        if (action.currency or "").upper() != (evidence.currency or "").upper():
            reasons.append("cash dividend currency mismatch")

    if action.action_type == CorporateActionType.STOCK_DIVIDEND:
        if not _close_decimal(action.stock_ratio, evidence.stock_ratio, tolerance):
            reasons.append("stock dividend ratio mismatch")

    if action.action_type == CorporateActionType.SPINOFF:
        if not _close_decimal(action.stock_ratio, evidence.stock_ratio, tolerance):
            reasons.append("spinoff ratio mismatch")
        if not evidence.outturn_identifier:
            reasons.append("spinoff outturn identifier missing")
        elif expected_outturn_identifier and evidence.outturn_identifier != expected_outturn_identifier:
            reasons.append("spinoff outturn identifier mismatch")

    if action.action_type in {CorporateActionType.MERGER, CorporateActionType.ACQUISITION}:
        if not _close_decimal(action.cash_amount, evidence.cash_amount, tolerance):
            reasons.append("merger cash consideration mismatch")
        if action.cash_amount is not None and (action.currency or "").upper() != (evidence.currency or "").upper():
            reasons.append("merger cash currency mismatch")
        if not _close_decimal(action.stock_ratio, evidence.stock_ratio, tolerance):
            reasons.append("merger stock consideration mismatch")
        if action.stock_ratio is not None and action.stock_ratio > ZERO and not evidence.outturn_identifier:
            reasons.append("merger successor identifier missing")
        elif expected_outturn_identifier and evidence.outturn_identifier != expected_outturn_identifier:
            reasons.append("merger successor identifier mismatch")

    if action.action_type in {
        CorporateActionType.BANKRUPTCY,
        CorporateActionType.LIQUIDATION,
        CorporateActionType.DELISTING,
    }:
        if action.cash_amount is not None and not _close_decimal(action.cash_amount, evidence.cash_amount, tolerance):
            reasons.append("terminal consideration mismatch")
        if action.cash_amount is not None and (action.currency or "").upper() != (evidence.currency or "").upper():
            reasons.append("terminal consideration currency mismatch")

    if reasons:
        return ReconciliationResult(
            action_id=action.action_id,
            provider=evidence.provider,
            provider_event_id=evidence.provider_event_id,
            status=ReconciliationStatus.MISMATCH,
            reasons=tuple(reasons),
        )
    return ReconciliationResult(
        action_id=action.action_id,
        provider=evidence.provider,
        provider_event_id=evidence.provider_event_id,
        status=ReconciliationStatus.PASS,
        reasons=(),
    )


def reconcile_action_set(
    actions: Iterable[CorporateAction],
    evidence_rows: Iterable[ProviderCorporateActionEvidence],
    *,
    decision_at: datetime | None = None,
) -> tuple[ReconciliationResult, ...]:
    """Reconcile a batch of kernel actions to point-in-time provider evidence.

    ``decision_at`` is the reconciliation cut-off.  Rows learned after that
    instant are invisible.  This matters when the same provider later corrects
    or cancels an action: the later revision cannot rewrite an earlier
    historical decision.

    Matching is deliberately conservative.  The provider event ID is first
    resolved to its latest known revision; if more than one distinct provider
    event remains for the same action type/effective date, the match is
    ambiguous and therefore BLOCKED rather than guessed.
    """
    if decision_at is not None:
        decision_at = require_aware(decision_at, "decision_at")

    by_type_date: dict[tuple[CorporateActionType, object], list[ProviderCorporateActionEvidence]] = {}
    for evidence in evidence_rows:
        if decision_at is not None and evidence.available_at > decision_at:
            continue
        by_type_date.setdefault((evidence.action_type, evidence.effective_at.date()), []).append(evidence)

    results: list[ReconciliationResult] = []
    for action in actions:
        candidates = by_type_date.get((action.action_type, action.effective_at.date()), [])
        if not candidates:
            results.append(
                ReconciliationResult(
                    action_id=action.action_id,
                    provider="NONE",
                    provider_event_id="NONE",
                    status=ReconciliationStatus.BLOCKED,
                    reasons=("no provider evidence for action type/effective date at reconciliation cut-off",),
                )
            )
            continue

        latest_per_event: list[ProviderCorporateActionEvidence] = []
        event_ids = sorted({row.provider_event_id for row in candidates})
        event_conflict: ReconciliationResult | None = None
        for event_id in event_ids:
            event_rows = [row for row in candidates if row.provider_event_id == event_id]
            latest_key = max((row.available_at, row.revision) for row in event_rows)
            latest = [row for row in event_rows if (row.available_at, row.revision) == latest_key]
            if len({repr(row) for row in latest}) != 1:
                event_conflict = ReconciliationResult(
                    action_id=action.action_id,
                    provider=latest[0].provider,
                    provider_event_id=event_id,
                    status=ReconciliationStatus.BLOCKED,
                    reasons=("conflicting latest provider revisions",),
                )
                break
            latest_per_event.append(latest[0])

        if event_conflict is not None:
            results.append(event_conflict)
            continue

        if len(latest_per_event) != 1:
            results.append(
                ReconciliationResult(
                    action_id=action.action_id,
                    provider=",".join(sorted({row.provider for row in latest_per_event})) or "NONE",
                    provider_event_id=",".join(row.provider_event_id for row in latest_per_event) or "NONE",
                    status=ReconciliationStatus.BLOCKED,
                    reasons=("multiple distinct provider events match action type/effective date",),
                )
            )
            continue

        results.append(reconcile_corporate_action(action, latest_per_event[0]))
    return tuple(results)

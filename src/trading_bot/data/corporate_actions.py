"""As-of corporate-action adjustment primitives."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from .contracts import CorporateAction, CorporateActionType
from .errors import DataContractError
from .time_utils import require_aware


SPLIT_TYPES = {CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT}


def split_adjustment_factor(
    *,
    instrument_id: UUID,
    price_observed_at: datetime,
    decision_at: datetime,
    actions: Iterable[CorporateAction],
) -> Decimal:
    """Return an as-of split price factor for a historical raw price.

    For a 2-for-1 split, pre-split prices receive factor ``1/2``. Only actions
    effective after the price observation and both effective and available by
    the decision timestamp are included.
    """
    observed = require_aware(price_observed_at, "price_observed_at")
    decision = require_aware(decision_at, "decision_at")
    if decision < observed:
        raise DataContractError("decision_at cannot precede price_observed_at")

    latest_by_action: dict[str, CorporateAction] = {}
    for action in actions:
        if (
            action.instrument_id != instrument_id
            or action.action_type not in SPLIT_TYPES
            or not (observed < action.effective_at <= decision)
            or action.available_at > decision
        ):
            continue
        current = latest_by_action.get(action.action_id)
        if current is None:
            latest_by_action[action.action_id] = action
            continue
        candidate_key = (action.available_at, action.revision)
        current_key = (current.available_at, current.revision)
        if candidate_key == current_key and action != current:
            raise DataContractError(
                f"conflicting corporate-action revision for {action.action_id}"
            )
        if candidate_key > current_key:
            latest_by_action[action.action_id] = action

    factor = Decimal("1")
    for action in sorted(
        latest_by_action.values(),
        key=lambda item: (item.effective_at, item.available_at, item.revision, item.action_id),
    ):
        assert action.split_new_shares is not None
        assert action.split_old_shares is not None
        factor *= action.split_old_shares / action.split_new_shares
    return factor


def adjusted_close_as_of(
    raw_close: Decimal,
    *,
    instrument_id: UUID,
    price_observed_at: datetime,
    decision_at: datetime,
    actions: Iterable[CorporateAction],
) -> Decimal:
    if raw_close <= 0:
        raise DataContractError("raw_close must be positive")
    return raw_close * split_adjustment_factor(
        instrument_id=instrument_id,
        price_observed_at=price_observed_at,
        decision_at=decision_at,
        actions=actions,
    )


def unresolved_material_action_exists(
    *,
    instrument_id: UUID,
    decision_at: datetime,
    actions: Iterable[CorporateAction],
    supported_types: set[CorporateActionType] | None = None,
) -> bool:
    decision = require_aware(decision_at, "decision_at")
    supported = supported_types or set(CorporateActionType)
    return any(
        action.instrument_id == instrument_id
        and action.available_at <= decision
        and action.effective_at <= decision
        and action.action_type not in supported
        for action in actions
    )

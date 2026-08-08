"""Normalization helpers for EDI Worldwide Corporate Actions trial exports.

The public developer documentation exposes the historical WCA response schema,
including EvtChangeDT, EventCreateDT, effective/ex dates, ratios, outturn IDs,
and event status. Authentication is intentionally not guessed here; the paid
trial must use the contract supplied with the approved EDI account.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Mapping

from ..contracts import CorporateActionType
from ..corporate_action_reconciliation import EvidenceStatus, ProviderCorporateActionEvidence
from ..errors import DataContractError

UTC = timezone.utc


def _get(row: Mapping[str, object], *names: str) -> object | None:
    lower = {str(k).lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lower:
            value = lower[name.lower()]
            if value not in (None, ""):
                return value
    return None


def _decimal(value: object | None) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def _datetime(value: object | None, *, end_of_day_if_date_only: bool = False) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        result = datetime.fromisoformat(text)
    except ValueError:
        result = datetime.strptime(text, "%m/%d/%Y %H:%M:%S")
    if result.tzinfo is None:
        if len(text) <= 10 and end_of_day_if_date_only:
            result = datetime.combine(result.date(), time(23, 59, 59))
        result = result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def canonical_ratio(
    ratio_old: Decimal | None,
    ratio_new: Decimal | None,
    *,
    semantics: str,
) -> Decimal | None:
    if ratio_old is None or ratio_new is None:
        return None
    if ratio_old <= 0 or ratio_new < 0:
        raise DataContractError("provider ratios must be non-negative with positive old ratio")
    if semantics == "TOTAL_NEW_OVER_OLD":
        return ratio_new / ratio_old
    if semantics == "ADDITIONAL_NEW_OVER_OLD":
        return ONE + ratio_new / ratio_old
    raise DataContractError(f"unsupported ratio semantics: {semantics}")


ONE = Decimal("1")


def parse_edi_evidence(
    row: Mapping[str, object],
    *,
    action_type: CorporateActionType,
    source_snapshot_id: str,
    ratio_semantics: str = "TOTAL_NEW_OVER_OLD",
) -> ProviderCorporateActionEvidence:
    event_id = _get(row, "EvtUniqueID", "EventID")
    available_at = _datetime(_get(row, "EvtChangeDT", "LstChangeDT"))
    effective_at = _datetime(_get(row, "ExDT", "EffectiveDT"), end_of_day_if_date_only=True)
    if event_id is None or available_at is None or effective_at is None:
        raise DataContractError("EDI evidence requires event ID, change timestamp, and effective/ex date")

    raw_status = str(_get(row, "EvtActionCD") or "I").upper()
    status = EvidenceStatus.CANCELLED if raw_status == "C" else EvidenceStatus.DELETED if raw_status in {"D", "Q"} else EvidenceStatus.ACTIVE
    ratio_old = _decimal(_get(row, "RatioOld"))
    ratio_new = _decimal(_get(row, "RatioNew"))
    multiplier = canonical_ratio(ratio_old, ratio_new, semantics=ratio_semantics) if action_type in {CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT} else None
    stock_ratio = None
    if action_type in {CorporateActionType.STOCK_DIVIDEND, CorporateActionType.SPINOFF} and ratio_old is not None and ratio_new is not None:
        # For distributions, the canonical contract stores incremental new shares.
        if ratio_semantics == "ADDITIONAL_NEW_OVER_OLD":
            stock_ratio = ratio_new / ratio_old
        else:
            stock_ratio = ratio_new / ratio_old - ONE
            if stock_ratio < 0:
                raise DataContractError("stock distribution ratio cannot be negative")

    cash = _decimal(_get(row, "grossdividend", "settlementamount", "pricepershare"))
    currency = str(_get(row, "RateCurenCD", "TradingCurenCD") or "").upper() or None
    outturn = _get(row, "OutIsin", "OutUSCode", "OutFigi", "OutLocalCode")

    return ProviderCorporateActionEvidence(
        provider="EDI_WCA",
        provider_event_id=str(event_id),
        action_type=action_type,
        effective_at=effective_at,
        available_at=available_at,
        source_snapshot_id=source_snapshot_id,
        status=status,
        share_multiplier=multiplier,
        cash_amount=cash,
        currency=currency if cash is not None else None,
        stock_ratio=stock_ratio,
        outturn_identifier=str(outturn) if outturn is not None else None,
        metadata={
            "event_code": str(_get(row, "EventCD") or ""),
            "event_create_dt": str(_get(row, "EventCreateDT") or ""),
            "notes_text": str(_get(row, "NotesText") or ""),
            "raw_action_code": raw_status,
        },
    )

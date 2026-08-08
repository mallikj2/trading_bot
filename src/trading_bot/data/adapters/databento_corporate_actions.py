"""Approval-gated Databento corporate-actions trial adapter."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
import os
from typing import Any, Callable, Mapping

from ..contracts import CorporateActionType
from ..corporate_action_reconciliation import EvidenceStatus, ProviderCorporateActionEvidence
from ..errors import DataContractError

UTC = timezone.utc
ONE = Decimal("1")


class DatabentoCorporateActionsLicenseError(PermissionError):
    pass


def _approved(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def _default_reference_factory(api_key: str) -> Any:
    try:
        import databento as db  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError("Databento SDK is required for credentialed corporate-action trials") from exc
    return db.Reference(api_key)


@dataclass(slots=True)
class DatabentoCorporateActionsClient:
    api_key: str | None = None
    license_approved: bool | None = None
    reference_factory: Callable[[str], Any] = _default_reference_factory

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("DATABENTO_API_KEY")
        env = _approved(os.getenv("DATABENTO_CORPORATE_ACTIONS_LICENSE_APPROVED"))
        self.license_approved = env if self.license_approved is None else self.license_approved
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY is required")
        if not self.license_approved:
            raise DatabentoCorporateActionsLicenseError(
                "explicit Databento corporate-actions license approval is required before the trial"
            )

    def get_range(
        self,
        *,
        symbols: list[str] | str,
        start: date | datetime | str,
        end: date | datetime | str | None = None,
        events: list[str] | None = None,
        pit: bool = True,
    ) -> Any:
        client = self.reference_factory(str(self.api_key))
        kwargs: dict[str, Any] = {
            "symbols": symbols,
            "start": start,
            "countries": ["US"],
            "pit": pit,
        }
        if end is not None:
            kwargs["end"] = end
        if events:
            kwargs["events"] = events
        return client.corporate_actions.get_range(**kwargs)


def _as_decimal(value: object | None) -> Decimal | None:
    if value in (None, "", "nan"):
        return None
    return Decimal(str(value))


def _as_utc(value: object | None, *, end_of_day_if_date_only: bool = False) -> datetime:
    if value in (None, ""):
        raise DataContractError("timestamp/date is required")
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime.combine(value, time(23, 59, 59) if end_of_day_if_date_only else time.min)
    else:
        text = str(value).replace("Z", "+00:00")
        result = datetime.fromisoformat(text)
    if result.tzinfo is None:
        result = result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def parse_databento_evidence(
    row: Mapping[str, object],
    *,
    action_type: CorporateActionType,
    source_snapshot_id: str,
) -> ProviderCorporateActionEvidence:
    event_id = row.get("event_unique_id") or row.get("event_id")
    ts_record = row.get("ts_record")
    effective = row.get("ex_date") or row.get("effective_date") or row.get("event_date")
    if not event_id or ts_record in (None, "") or effective in (None, ""):
        raise DataContractError("Databento evidence requires event_unique_id, ts_record, and event/effective date")

    action = str(row.get("action") or "I").upper()
    status = EvidenceStatus.CANCELLED if action in {"C", "P"} else EvidenceStatus.DELETED if action in {"D", "Q"} else EvidenceStatus.ACTIVE
    ratio_old = _as_decimal(row.get("ratio_old"))
    ratio_new = _as_decimal(row.get("ratio_new"))
    share_multiplier = None
    stock_ratio = None
    if action_type in {CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT} and ratio_old and ratio_new is not None:
        share_multiplier = ratio_new / ratio_old
    if action_type in {CorporateActionType.STOCK_DIVIDEND, CorporateActionType.SPINOFF} and ratio_old and ratio_new is not None:
        # Databento documents ratio_new for FSPLT/DIV/BON as including existing holdings.
        stock_ratio = ratio_new / ratio_old - ONE
        if stock_ratio < 0:
            raise DataContractError("Databento stock distribution ratio cannot be negative")

    cash = _as_decimal(row.get("gross_dividend") or row.get("declared_gross_amount") or row.get("settlement_amount"))
    currency = str(row.get("currency") or row.get("declared_currency") or "").upper() or None
    outturn = row.get("out_isin") or row.get("out_security_id") or row.get("new_isin")

    return ProviderCorporateActionEvidence(
        provider="DATABENTO_CA",
        provider_event_id=str(event_id),
        action_type=action_type,
        effective_at=_as_utc(effective, end_of_day_if_date_only=True),
        available_at=_as_utc(ts_record),
        source_snapshot_id=source_snapshot_id,
        status=status,
        share_multiplier=share_multiplier,
        cash_amount=cash,
        currency=currency if cash is not None else None,
        stock_ratio=stock_ratio,
        outturn_identifier=str(outturn) if outturn is not None else None,
        metadata={"event": str(row.get("event") or ""), "event_subtype": str(row.get("event_subtype") or "")},
    )

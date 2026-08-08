"""Approval-gated Databento PIT security-master and exact-execution companion.

The adapter deliberately separates provider *effective* timestamps from provider
*record* timestamps.  A historical attribute may be economically effective at
``ts_effective`` but it is not allowed into a simulated decision before
``ts_record`` says that version existed in the provider's PIT stream.

The module accepts SDK DataFrame / DBNStore-like responses without importing
pandas at runtime.  Credentialed environments may install the pinned Databento
SDK; the cumulative Phase 02 unit suite remains dependency-free.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import os
from typing import Any, Callable, Iterable, Mapping, Sequence
from uuid import UUID, NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from ..contracts import ListingState, SecurityType
from ..errors import DataContractError, PointInTimeError
from ..time_utils import require_aware

NEW_YORK = ZoneInfo("America/New_York")


class DatabentoCompanionError(DataContractError):
    pass


class DatabentoLicenseError(PermissionError):
    pass


def _approved(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def _default_reference_factory(api_key: str) -> Any:
    try:
        import databento as db  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - credentialed environment only
        raise DatabentoCompanionError(
            "Databento SDK is required for the credentialed companion trial; install the approved pinned version"
        ) from exc
    return db.Reference(api_key)


def _default_historical_factory(api_key: str) -> Any:
    try:
        import databento as db  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - credentialed environment only
        raise DatabentoCompanionError(
            "Databento SDK is required for the credentialed companion trial; install the approved pinned version"
        ) from exc
    return db.Historical(api_key)


@dataclass(slots=True)
class DatabentoCompanionClient:
    api_key: str | None = None
    license_approved: bool | None = None
    reference_factory: Callable[[str], Any] = _default_reference_factory
    historical_factory: Callable[[str], Any] = _default_historical_factory

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("DATABENTO_API_KEY")
        env_approved = _approved(os.getenv("DATABENTO_RESEARCH_LICENSE_APPROVED"))
        self.license_approved = env_approved if self.license_approved is None else self.license_approved
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY is required")
        if not self.license_approved:
            raise DatabentoLicenseError(
                "Databento research-license approval flag is required before the PIT/execution companion trial"
            )

    def security_master_range(
        self,
        *,
        start: date | datetime | str,
        end: date | datetime | str | None = None,
        symbol: str | None = None,
        stype_in: str = "raw_symbol",
        us_equities_only: bool = True,
    ) -> Any:
        client = self.reference_factory(str(self.api_key))
        kwargs: dict[str, Any] = {
            "start": start,
            "index": "ts_effective",
        }
        if symbol is not None:
            if not symbol.strip():
                raise ValueError("symbol cannot be blank")
            kwargs["symbols"] = [symbol]
            kwargs["stype_in"] = stype_in
        if us_equities_only:
            kwargs["countries"] = ["US"]
            kwargs["security_types"] = ["EQS"]
        if end is not None:
            kwargs["end"] = end
        return client.security_master.get_range(**kwargs)

    def historical_trades(
        self,
        *,
        dataset: str,
        symbol: str,
        start: datetime | str,
        end: datetime | str,
        stype_in: str = "figi",
    ) -> Any:
        if not dataset.strip():
            raise ValueError("dataset is required and must be confirmed from the approved Databento account")
        if not symbol.strip():
            raise ValueError("symbol is required")
        if stype_in not in {"figi", "isin", "us_code", "raw_symbol", "nasdaq_symbol"}:
            raise ValueError("unsupported Databento trade input symbology")
        client = self.historical_factory(str(self.api_key))
        return client.timeseries.get_range(
            dataset=dataset,
            schema="trades",
            symbols=[symbol],
            stype_in=stype_in,
            start=start,
            end=end,
        )


def dataframe_row_count(value: Any) -> int:
    """Return a deterministic row count for SDK DataFrame/DBNStore-like responses."""
    if hasattr(value, "to_df"):
        value = value.to_df()
    try:
        return int(len(value))
    except (TypeError, ValueError) as exc:
        raise DatabentoCompanionError("Databento response is not row-countable") from exc


def _records(value: Any) -> tuple[Mapping[str, Any], ...]:
    """Normalize a Databento DataFrame, DBNStore or list-of-mappings to records."""
    if hasattr(value, "to_df"):
        value = value.to_df()
    if hasattr(value, "reset_index") and hasattr(value, "to_dict"):
        value = value.reset_index().to_dict(orient="records")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DatabentoCompanionError("Databento response cannot be normalized to records")
    rows: list[Mapping[str, Any]] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise DatabentoCompanionError("Databento response row is not a mapping")
        rows.append(row)
    return tuple(rows)


def _timestamp(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            raise DatabentoCompanionError(f"{field} is required")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise DatabentoCompanionError(f"invalid {field}: {value!r}") from exc
    return require_aware(parsed, field)


def _optional_date(value: Any, field: str) -> date | None:
    if value is None or str(value).strip() in {"", "NaT", "nan", "None"}:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError as exc:
        raise DatabentoCompanionError(f"invalid {field}: {value!r}") from exc


def _optional_decimal(value: Any, field: str) -> Decimal | None:
    if value is None or str(value).strip() in {"", "NaN", "nan", "None"}:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DatabentoCompanionError(f"invalid {field}: {value!r}") from exc
    if not result.is_finite():
        raise DatabentoCompanionError(f"non-finite {field}")
    return result


def internal_instrument_id(provider_security_id: str) -> UUID:
    provider_id = provider_security_id.strip()
    if not provider_id:
        raise DatabentoCompanionError("provider security_id is required")
    return uuid5(NAMESPACE_URL, f"quant-trading-bot:databento-security:{provider_id}")


_EXCHANGE_MAP = {
    "USNYSE": "NYSE",
    "USNASD": "NASDAQ",
}

_SECURITY_TYPE_MAP = {
    "EQS": SecurityType.COMMON_STOCK,
    "ETF": SecurityType.ETF,
    "PRF": SecurityType.PREFERRED,
    "WAR": SecurityType.WARRANT,
    "TRT": SecurityType.RIGHT,
    "UNT": SecurityType.UNIT,
}

_LISTED = {"L", "N", "R", "T"}
_SUSPENDED = {"S", "V", "I"}
_DELISTED = {"D", "H", "U"}


@dataclass(frozen=True, slots=True)
class DatabentoPitListing:
    instrument_id: UUID
    provider_listing_id: str
    provider_security_id: str
    provider_issuer_id: str
    symbol: str | None
    nasdaq_symbol: str | None
    figi: str | None
    us_code: str | None
    cik: str | None
    exchange: str | None
    security_type: SecurityType
    listing_state: ListingState
    listing_source: str
    effective_at: datetime
    available_at: datetime
    listing_date: date | None
    delisting_date: date | None
    shares_outstanding: Decimal | None
    shares_outstanding_date: date | None
    source_snapshot_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective_at", require_aware(self.effective_at, "effective_at"))
        object.__setattr__(self, "available_at", require_aware(self.available_at, "available_at"))
        if not self.provider_listing_id.strip() or not self.provider_security_id.strip():
            raise DatabentoCompanionError("provider listing/security identifiers are required")
        if not self.source_snapshot_id.strip():
            raise DatabentoCompanionError("source_snapshot_id is required")
        if self.shares_outstanding is not None and self.shares_outstanding <= 0:
            raise DatabentoCompanionError("shares_outstanding must be positive")
        if self.shares_outstanding is not None and self.shares_outstanding_date is None:
            raise DatabentoCompanionError("shares_outstanding requires shares_outstanding_date")


def normalize_security_master(
    value: Any,
    *,
    source_snapshot_id: str,
) -> tuple[DatabentoPitListing, ...]:
    rows = _records(value)
    if not rows:
        raise DatabentoCompanionError("security-master response is empty")
    normalized: list[DatabentoPitListing] = []
    for row in rows:
        listing_id = str(row.get("listing_id", "")).strip()
        security_id = str(row.get("security_id", "")).strip()
        issuer_id = str(row.get("issuer_id", "")).strip()
        if not listing_id or not security_id or not issuer_id:
            raise DatabentoCompanionError("security-master row lacks stable provider identifiers")
        raw_status = str(row.get("listing_status", "")).strip()
        if raw_status in _LISTED:
            state = ListingState.LISTED
        elif raw_status in _SUSPENDED:
            state = ListingState.SUSPENDED
        elif raw_status in _DELISTED:
            state = ListingState.DELISTED
        else:
            state = ListingState.INACTIVE
        raw_type = str(row.get("security_type", "")).strip()
        security_type = _SECURITY_TYPE_MAP.get(raw_type, SecurityType.OTHER)
        raw_primary = str(row.get("primary_exchange", "")).strip()
        exchange = _EXCHANGE_MAP.get(raw_primary)
        cik_raw = str(row.get("cik", "")).strip()
        cik = cik_raw.zfill(10) if cik_raw.isdigit() and int(cik_raw) > 0 else None
        shares = _optional_decimal(row.get("shares_outstanding"), "shares_outstanding")
        shares_date = _optional_date(row.get("shares_outstanding_date"), "shares_outstanding_date")
        normalized.append(
            DatabentoPitListing(
                instrument_id=internal_instrument_id(security_id),
                provider_listing_id=listing_id,
                provider_security_id=security_id,
                provider_issuer_id=issuer_id,
                symbol=(str(row.get("symbol")).strip() if row.get("symbol") not in (None, "") else None),
                nasdaq_symbol=(str(row.get("nasdaq_symbol")).strip() if row.get("nasdaq_symbol") not in (None, "") else None),
                figi=(str(row.get("figi")).strip() if row.get("figi") not in (None, "") else None),
                us_code=(str(row.get("us_code")).strip() if row.get("us_code") not in (None, "") else None),
                cik=cik,
                exchange=exchange,
                security_type=security_type,
                listing_state=state,
                listing_source=str(row.get("listing_source", "")).strip(),
                effective_at=_timestamp(row.get("ts_effective"), "ts_effective"),
                available_at=_timestamp(row.get("ts_record"), "ts_record"),
                listing_date=_optional_date(row.get("listing_date"), "listing_date"),
                delisting_date=_optional_date(row.get("delisting_date"), "delisting_date"),
                shares_outstanding=shares,
                shares_outstanding_date=shares_date,
                source_snapshot_id=source_snapshot_id,
            )
        )
    return tuple(sorted(normalized, key=lambda x: (x.provider_listing_id, x.effective_at, x.available_at)))


def select_primary_listing_as_of(
    observations: Iterable[DatabentoPitListing],
    *,
    instrument_id: UUID,
    decision_at: datetime,
) -> DatabentoPitListing:
    decision = require_aware(decision_at, "decision_at")
    eligible = [
        row
        for row in observations
        if row.instrument_id == instrument_id
        and row.listing_source == "M"
        and row.effective_at <= decision
        and row.available_at <= decision
    ]
    if not eligible:
        raise PointInTimeError("no primary security-master record was known by decision_at")
    latest_effective = max(row.effective_at for row in eligible)
    latest = [row for row in eligible if row.effective_at == latest_effective]
    latest_available = max(row.available_at for row in latest)
    latest = [row for row in latest if row.available_at == latest_available]
    identities = {
        (
            row.provider_listing_id,
            row.provider_security_id,
            row.cik,
            row.exchange,
            row.security_type,
            row.listing_state,
            row.figi,
            row.us_code,
            row.shares_outstanding,
            row.shares_outstanding_date,
        )
        for row in latest
    }
    if len(identities) != 1:
        raise PointInTimeError("conflicting latest PIT security-master rows")
    return latest[0]


def find_ticker_reuse(
    observations: Iterable[DatabentoPitListing],
) -> dict[str, tuple[str, ...]]:
    """Return symbols observed for more than one stable provider security ID."""
    by_symbol: dict[str, set[str]] = {}
    for row in observations:
        symbol = (row.nasdaq_symbol or row.symbol or "").strip()
        if not symbol:
            continue
        by_symbol.setdefault(symbol, set()).add(row.provider_security_id)
    return {
        symbol: tuple(sorted(ids))
        for symbol, ids in sorted(by_symbol.items())
        if len(ids) > 1
    }


@dataclass(frozen=True, slots=True)
class DatabentoTrade:
    provider_instrument_id: int
    ts_event: datetime
    ts_recv: datetime
    price: Decimal
    size: int
    flags: int
    publisher_id: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "ts_event", require_aware(self.ts_event, "ts_event"))
        object.__setattr__(self, "ts_recv", require_aware(self.ts_recv, "ts_recv"))
        if self.provider_instrument_id <= 0 or self.publisher_id < 0:
            raise DatabentoCompanionError("trade identifiers are invalid")
        if self.price <= 0 or self.size <= 0:
            raise DatabentoCompanionError("trade price and size must be positive")
        if self.flags < 0 or self.flags > 255:
            raise DatabentoCompanionError("trade flags must fit uint8")


def normalize_trades(value: Any) -> tuple[DatabentoTrade, ...]:
    rows = _records(value)
    if not rows:
        raise DatabentoCompanionError("trade response is empty")
    output: list[DatabentoTrade] = []
    for row in rows:
        action = str(row.get("action", "T")).strip()
        if action not in {"T", "Trade", ""}:
            raise DatabentoCompanionError(f"non-trade action in trades schema: {action!r}")
        try:
            provider_instrument_id = int(row["instrument_id"])
            publisher_id = int(row.get("publisher_id", 0))
            size = int(row["size"])
            flags = int(row.get("flags", 0))
            price = Decimal(str(row["price"]))
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise DatabentoCompanionError("invalid Databento trade row") from exc
        output.append(
            DatabentoTrade(
                provider_instrument_id=provider_instrument_id,
                ts_event=_timestamp(row.get("ts_event"), "ts_event"),
                ts_recv=_timestamp(row.get("ts_recv", row.get("ts_event")), "ts_recv"),
                price=price,
                size=size,
                flags=flags,
                publisher_id=publisher_id,
            )
        )
    return tuple(sorted(output, key=lambda row: (row.ts_event, row.ts_recv, row.publisher_id)))


@dataclass(frozen=True, slots=True)
class ExactExecutionVwap:
    session_date: date
    window_start: datetime
    window_end: datetime
    trade_count: int
    total_volume: int
    vwap: Decimal
    first_trade_at: datetime
    last_trade_at: datetime
    provider_instrument_ids: tuple[int, ...]
    publisher_ids: tuple[int, ...]


def exact_trade_vwap(
    trades: Iterable[DatabentoTrade],
    *,
    session_date: date,
    start_time: time = time(10, 0),
    end_time: time = time(10, 30),
    reject_quality_flags: int = 0b00001100,  # BAD_TS_RECV or MAYBE_BAD_BOOK
) -> ExactExecutionVwap:
    if end_time <= start_time:
        raise ValueError("execution window end must be after start")
    selected: list[DatabentoTrade] = []
    for row in trades:
        local = row.ts_event.astimezone(NEW_YORK)
        local_time = local.time().replace(tzinfo=None)
        if local.date() != session_date or not (start_time <= local_time < end_time):
            continue
        if row.flags & reject_quality_flags:
            raise DatabentoCompanionError("execution trade carries a rejected data-quality flag")
        selected.append(row)
    if not selected:
        raise DatabentoCompanionError("no trades in exact execution window")
    ids = {row.provider_instrument_id for row in selected}
    if len(ids) != 1:
        raise DatabentoCompanionError("execution window contains multiple provider instrument IDs")
    total_volume = sum(row.size for row in selected)
    weighted = sum((row.price * row.size for row in selected), Decimal("0"))
    start_local = datetime.combine(session_date, start_time, tzinfo=NEW_YORK)
    end_local = datetime.combine(session_date, end_time, tzinfo=NEW_YORK)
    return ExactExecutionVwap(
        session_date=session_date,
        window_start=start_local,
        window_end=end_local,
        trade_count=len(selected),
        total_volume=total_volume,
        vwap=weighted / Decimal(total_volume),
        first_trade_at=min(row.ts_event for row in selected),
        last_trade_at=max(row.ts_event for row in selected),
        provider_instrument_ids=tuple(sorted(ids)),
        publisher_ids=tuple(sorted({row.publisher_id for row in selected})),
    )

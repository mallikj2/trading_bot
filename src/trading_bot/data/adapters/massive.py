"""Production-oriented, read-only Massive stock-data adapter."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import os
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID
from zoneinfo import ZoneInfo

from ..contracts import (
    CorporateAction,
    CorporateActionType,
    DailyBar,
    DataQualityStatus,
    MarketCapObservation,
    SectorObservation,
    SymbolAlias,
)
from ..errors import DataContractError, PointInTimeError
from ..time_utils import require_aware
from .http import JsonTransport, SafeJsonClient
from .models import AvailabilitySemantics, IntradayBar, TickerReference

UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")


class MassiveSchemaError(DataContractError):
    pass


class MassiveClient:
    base_url = "https://api.massive.com"
    adapter_version = "MASSIVE-STOCKS-v0.2.0"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: JsonTransport | None = None,
        requests_per_second: float = 5.0,
    ) -> None:
        self.api_key = api_key or os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("MASSIVE_API_KEY is required")
        self._http = SafeJsonClient(
            base_url=self.base_url,
            default_headers={"Accept": "application/json", "User-Agent": "quant-trading-bot/0.2"},
            transport=transport,
            requests_per_second=requests_per_second,
        )

    def _with_key(self, path_or_url: str, params: Mapping[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        query = dict(params or {})
        parsed = urlparse(path_or_url)
        existing = {key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
        if "apikey" not in existing:
            query["apiKey"] = self.api_key
        return path_or_url, query

    def get_json(self, path_or_url: str, *, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        path, query = self._with_key(path_or_url, params)
        payload = self._http.get_json(path, params=query)
        status = payload.get("status")
        if status not in (None, "OK", "DELAYED"):
            raise MassiveSchemaError(f"Massive response status is not usable: {status!r}")
        return payload

    def iter_results(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        max_pages: int = 10000,
    ) -> Iterator[Mapping[str, Any]]:
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        next_url: str | None = path
        next_params = dict(params or {})
        pages = 0
        while next_url:
            pages += 1
            if pages > max_pages:
                raise MassiveSchemaError("pagination exceeded max_pages")
            payload = self.get_json(next_url, params=next_params)
            results = payload.get("results", [])
            if isinstance(results, Mapping):
                yield results
            elif isinstance(results, Sequence) and not isinstance(results, (str, bytes, bytearray)):
                for row in results:
                    if not isinstance(row, Mapping):
                        raise MassiveSchemaError("Massive results must contain JSON objects")
                    yield row
            else:
                raise MassiveSchemaError("Massive results must be an object or array")
            candidate = payload.get("next_url")
            if candidate is not None and not isinstance(candidate, str):
                raise MassiveSchemaError("Massive next_url must be a string")
            next_url = candidate
            next_params = {}

    def list_tickers(
        self,
        *,
        as_of_date: date,
        active: bool,
        exchange: str | None = None,
        ticker_type: str = "CS",
    ) -> tuple[Mapping[str, Any], ...]:
        params = {
            "market": "stocks",
            "locale": "us",
            "type": ticker_type,
            "date": as_of_date.isoformat(),
            "active": active,
            "exchange": exchange,
            "limit": 1000,
            "sort": "ticker",
            "order": "asc",
        }
        return tuple(self.iter_results("/v3/reference/tickers", params=params))

    def ticker_overview(self, ticker: str, *, as_of_date: date) -> Mapping[str, Any]:
        return self.get_json(
            f"/v3/reference/tickers/{ticker}",
            params={"date": as_of_date.isoformat()},
        )

    def aggregates(
        self,
        ticker: str,
        *,
        multiplier: int,
        timespan: str,
        start: date,
        end: date,
        adjusted: bool = False,
    ) -> tuple[Mapping[str, Any], ...]:
        if multiplier < 1:
            raise ValueError("multiplier must be positive")
        path = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start.isoformat()}/{end.isoformat()}"
        return tuple(
            self.iter_results(
                path,
                params={"adjusted": adjusted, "sort": "asc", "limit": 50000},
            )
        )

    def splits(self, *, ticker: str | None = None) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            self.iter_results(
                "/stocks/v1/splits",
                params={"ticker": ticker, "limit": 5000, "sort": "execution_date.asc"},
            )
        )

    def dividends(self, *, ticker: str | None = None) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            self.iter_results(
                "/stocks/v1/dividends",
                params={"ticker": ticker, "limit": 5000, "sort": "ex_dividend_date.asc"},
            )
        )

    def ticker_events(self, identifier: str) -> Mapping[str, Any]:
        return self.get_json(f"/vX/reference/tickers/{identifier}/events")


def _decimal(row: Mapping[str, Any], key: str) -> Decimal:
    value = row.get(key)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MassiveSchemaError(f"Massive field {key!r} is not numeric") from exc
    if not result.is_finite():
        raise MassiveSchemaError(f"Massive field {key!r} is not finite")
    return result


def _epoch_ms(row: Mapping[str, Any], key: str = "t") -> datetime:
    value = row.get(key)
    if not isinstance(value, (int, float)):
        raise MassiveSchemaError(f"Massive timestamp field {key!r} is required")
    return datetime.fromtimestamp(float(value) / 1000.0, tz=UTC)


def normalize_ticker_references(
    rows: Iterable[Mapping[str, Any]],
    *,
    as_of_date: date,
    as_of_available_at: datetime,
    source_snapshot_id: str,
    validated_historical_as_of_semantics: bool = False,
) -> tuple[TickerReference, ...]:
    if not validated_historical_as_of_semantics:
        raise PointInTimeError(
            "Massive ticker snapshots are blocked until credentialed point-in-time semantics are validated"
        )
    available_for_snapshot = require_aware(as_of_available_at, "as_of_available_at")
    normalized: list[TickerReference] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        ticker = str(row.get("ticker", "")).strip()
        mic = str(row.get("primary_exchange", "")).strip()
        key = (mic, ticker)
        if key in seen:
            raise MassiveSchemaError(f"duplicate ticker reference: {mic}:{ticker}")
        seen.add(key)
        available_at = available_for_snapshot
        delisted = row.get("delisted_utc")
        delisted_date = date.fromisoformat(str(delisted)[:10]) if delisted else None
        normalized.append(
            TickerReference(
                ticker=ticker,
                name=str(row.get("name", "")).strip(),
                primary_exchange_mic=mic,
                ticker_type=str(row.get("type", "")).strip(),
                active=bool(row.get("active")),
                as_of_date=as_of_date,
                available_at=available_at,
                source_snapshot_id=source_snapshot_id,
                cik=str(row["cik"]).zfill(10) if row.get("cik") else None,
                composite_figi=str(row["composite_figi"]) if row.get("composite_figi") else None,
                share_class_figi=str(row["share_class_figi"]) if row.get("share_class_figi") else None,
                delisted_date=delisted_date,
            )
        )
    if not normalized:
        raise MassiveSchemaError("ticker reference dataset is empty")
    return tuple(sorted(normalized, key=lambda item: (item.primary_exchange_mic, item.ticker)))


def normalize_daily_bars(
    rows: Iterable[Mapping[str, Any]],
    *,
    instrument_id: UUID,
    source_snapshot_id: str,
    session_close_at: Callable[[date], datetime],
    publication_delay: timedelta = timedelta(minutes=30),
) -> tuple[DailyBar, ...]:
    if publication_delay < timedelta(0):
        raise ValueError("publication_delay cannot be negative")
    bars: list[DailyBar] = []
    seen_dates: set[date] = set()
    for row in rows:
        timestamp = _epoch_ms(row)
        session_date = timestamp.astimezone(NEW_YORK).date()
        if session_date in seen_dates:
            raise MassiveSchemaError(f"duplicate daily aggregate for {session_date}")
        seen_dates.add(session_date)
        observed_at = require_aware(session_close_at(session_date), "session_close_at")
        bars.append(
            DailyBar(
                instrument_id=instrument_id,
                session_date=session_date,
                open=_decimal(row, "o"),
                high=_decimal(row, "h"),
                low=_decimal(row, "l"),
                close=_decimal(row, "c"),
                volume=int(row.get("v", -1)),
                observed_at=observed_at,
                available_at=observed_at + publication_delay,
                snapshot_id=source_snapshot_id,
                provider_revision=0,
                quality_status=DataQualityStatus.VALID,
            )
        )
    if not bars:
        raise MassiveSchemaError("daily aggregate dataset is empty")
    return tuple(sorted(bars, key=lambda item: item.session_date))


def normalize_intraday_bars(
    rows: Iterable[Mapping[str, Any]],
    *,
    instrument_id: UUID,
    symbol: str,
    source_snapshot_id: str,
    interval_minutes: int,
    availability_lag: timedelta = timedelta(seconds=5),
) -> tuple[IntradayBar, ...]:
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")
    if availability_lag < timedelta(0):
        raise ValueError("availability_lag cannot be negative")
    bars: list[IntradayBar] = []
    seen: set[datetime] = set()
    for row in rows:
        start = _epoch_ms(row)
        if start in seen:
            raise MassiveSchemaError(f"duplicate intraday aggregate at {start.isoformat()}")
        seen.add(start)
        end = start + timedelta(minutes=interval_minutes)
        bars.append(
            IntradayBar(
                instrument_id=instrument_id,
                symbol=symbol,
                session_date=start.astimezone(NEW_YORK).date(),
                interval_start=start,
                interval_end=end,
                open=_decimal(row, "o"),
                high=_decimal(row, "h"),
                low=_decimal(row, "l"),
                close=_decimal(row, "c"),
                volume=int(row.get("v", -1)),
                vwap=_decimal(row, "vw"),
                available_at=end + availability_lag,
                source_snapshot_id=source_snapshot_id,
                quality_status=DataQualityStatus.VALID,
            )
        )
    if not bars:
        raise MassiveSchemaError("intraday aggregate dataset is empty")
    return tuple(sorted(bars, key=lambda item: item.interval_start))


def normalize_splits(
    rows: Iterable[Mapping[str, Any]],
    *,
    instrument_id: UUID,
    source_snapshot_id: str,
    effective_at_for_date: Callable[[date], datetime],
) -> tuple[CorporateAction, ...]:
    actions: list[CorporateAction] = []
    for row in rows:
        action_id = str(row.get("id", "")).strip()
        execution = row.get("execution_date")
        if not action_id or not execution:
            raise MassiveSchemaError("split requires id and execution_date")
        execution_date = date.fromisoformat(str(execution))
        effective_at = require_aware(effective_at_for_date(execution_date), "effective_at")
        split_from = _decimal(row, "split_from")
        split_to = _decimal(row, "split_to")
        action_type = (
            CorporateActionType.REVERSE_SPLIT if split_from > split_to else CorporateActionType.SPLIT
        )
        actions.append(
            CorporateAction(
                action_id=action_id,
                instrument_id=instrument_id,
                action_type=action_type,
                effective_at=effective_at,
                available_at=effective_at,
                source_snapshot_id=source_snapshot_id,
                split_old_shares=split_from,
                split_new_shares=split_to,
                metadata={
                    "provider_adjustment_type": row.get("adjustment_type"),
                    "historical_adjustment_factor": row.get("historical_adjustment_factor"),
                    "availability_semantics": AvailabilitySemantics.EFFECTIVE_DATE_CONSERVATIVE.value,
                },
            )
        )
    return tuple(sorted(actions, key=lambda item: (item.effective_at, item.action_id)))


def normalize_dividends(
    rows: Iterable[Mapping[str, Any]],
    *,
    instrument_id: UUID,
    source_snapshot_id: str,
    effective_at_for_date: Callable[[date], datetime],
) -> tuple[CorporateAction, ...]:
    actions: list[CorporateAction] = []
    for row in rows:
        action_id = str(row.get("id", "")).strip()
        ex_date = row.get("ex_dividend_date")
        if not action_id or not ex_date:
            raise MassiveSchemaError("dividend requires id and ex_dividend_date")
        effective_at = require_aware(effective_at_for_date(date.fromisoformat(str(ex_date))), "effective_at")
        currency = str(row.get("currency", "")).upper()
        actions.append(
            CorporateAction(
                action_id=action_id,
                instrument_id=instrument_id,
                action_type=CorporateActionType.CASH_DIVIDEND,
                effective_at=effective_at,
                available_at=effective_at,
                source_snapshot_id=source_snapshot_id,
                cash_amount=_decimal(row, "cash_amount"),
                currency=currency,
                metadata={
                    "declaration_date": row.get("declaration_date"),
                    "record_date": row.get("record_date"),
                    "pay_date": row.get("pay_date"),
                    "distribution_type": row.get("distribution_type"),
                    "frequency": row.get("frequency"),
                    "historical_adjustment_factor": row.get("historical_adjustment_factor"),
                    "availability_semantics": AvailabilitySemantics.EFFECTIVE_DATE_CONSERVATIVE.value,
                },
            )
        )
    return tuple(sorted(actions, key=lambda item: (item.effective_at, item.action_id)))



def normalize_ticker_events(
    payload: Mapping[str, Any],
    *,
    instrument_id: UUID,
    exchange: str,
    source_snapshot_id: str,
    effective_at_for_date: Callable[[date], datetime],
) -> tuple[SymbolAlias, ...]:
    """Convert Massive ticker-change history to half-open alias intervals."""
    results = payload.get("results")
    if not isinstance(results, Mapping):
        raise MassiveSchemaError("ticker events results must be an object")
    events = results.get("events")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        raise MassiveSchemaError("ticker events must be an array")
    changes: list[tuple[datetime, str]] = []
    for event in events:
        if not isinstance(event, Mapping):
            raise MassiveSchemaError("ticker event must be an object")
        if event.get("type") != "ticker_change":
            raise MassiveSchemaError(f"unsupported ticker event type: {event.get('type')!r}")
        change = event.get("ticker_change")
        if not isinstance(change, Mapping):
            raise MassiveSchemaError("ticker_change payload is required")
        ticker = str(change.get("ticker", "")).strip()
        event_date = event.get("date")
        if not ticker or not event_date:
            raise MassiveSchemaError("ticker change requires ticker and date")
        effective = require_aware(effective_at_for_date(date.fromisoformat(str(event_date))), "effective_at")
        changes.append((effective, ticker))
    if not changes:
        raise MassiveSchemaError("ticker event history is empty")
    changes.sort(key=lambda item: (item[0], item[1]))
    if len({instant for instant, _ in changes}) != len(changes):
        raise MassiveSchemaError("multiple ticker changes share an effective timestamp")
    aliases: list[SymbolAlias] = []
    for index, (effective, ticker) in enumerate(changes):
        valid_to = changes[index + 1][0] if index + 1 < len(changes) else None
        aliases.append(
            SymbolAlias(
                instrument_id=instrument_id,
                symbol=ticker,
                exchange=exchange,
                valid_from=effective,
                valid_to=valid_to,
                provider_symbol=ticker,
                source_snapshot_id=source_snapshot_id,
                mapping_reason="MASSIVE_TICKER_CHANGE",
                available_at=effective,
            )
        )
    return tuple(aliases)


def _sic_division(sic_code: str) -> tuple[str, str]:
    try:
        value = int(sic_code)
    except ValueError as exc:
        raise MassiveSchemaError(f"invalid SIC code: {sic_code!r}") from exc
    ranges = (
        (100, 999, "A", "Agriculture, Forestry, and Fishing"),
        (1000, 1499, "B", "Mining"),
        (1500, 1799, "C", "Construction"),
        (2000, 3999, "D", "Manufacturing"),
        (4000, 4999, "E", "Transportation, Communications, Electric, Gas, and Sanitary Services"),
        (5000, 5199, "F", "Wholesale Trade"),
        (5200, 5999, "G", "Retail Trade"),
        (6000, 6799, "H", "Finance, Insurance, and Real Estate"),
        (7000, 8999, "I", "Services"),
        (9100, 9729, "J", "Public Administration"),
    )
    for lower, upper, code, label in ranges:
        if lower <= value <= upper:
            return code, label
    return "K", "Nonclassifiable Establishments"


def normalize_overview_sector(
    payload: Mapping[str, Any],
    *,
    instrument_id: UUID,
    effective_from: datetime,
    source_snapshot_id: str,
    validated_historical_as_of_semantics: bool = False,
) -> SectorObservation:
    if not validated_historical_as_of_semantics:
        raise PointInTimeError(
            "Massive ticker-overview SIC is blocked until historical as-of semantics are credential-validated"
        )
    result = payload.get("results")
    if not isinstance(result, Mapping):
        raise MassiveSchemaError("ticker overview results must be an object")
    sic = str(result.get("sic_code", "")).strip()
    if not sic:
        raise MassiveSchemaError("ticker overview lacks SIC code")
    sector_code, sector_label = _sic_division(sic)
    effective = require_aware(effective_from, "effective_from")
    return SectorObservation(
        instrument_id=instrument_id,
        taxonomy_id="SEC_SIC_DIVISION",
        taxonomy_version="V1",
        sector_code=sector_code,
        sector_label=sector_label,
        effective_from=effective,
        effective_to=None,
        available_at=effective,
        source_snapshot_id=source_snapshot_id,
    )


def normalize_overview_market_cap(
    payload: Mapping[str, Any],
    *,
    instrument_id: UUID,
    observed_at: datetime,
    source_snapshot_id: str,
    validated_historical_as_of_semantics: bool = False,
) -> MarketCapObservation:
    """Normalize provider market cap only after a credentialed as-of proof is approved."""
    if not validated_historical_as_of_semantics:
        raise PointInTimeError(
            "Massive ticker-overview market cap is blocked until historical as-of semantics are credential-validated"
        )
    result = payload.get("results")
    if not isinstance(result, Mapping):
        raise MassiveSchemaError("ticker overview results must be an object")
    cap = _decimal(result, "market_cap")
    observed = require_aware(observed_at, "observed_at")
    return MarketCapObservation(
        instrument_id=instrument_id,
        observed_at=observed,
        available_at=observed,
        market_cap=cap,
        source_snapshot_id=source_snapshot_id,
    )

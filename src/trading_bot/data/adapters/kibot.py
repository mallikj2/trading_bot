"""Kibot historical market-data adapter for Phase 02.

The adapter intentionally treats Kibot as a price/archive source, not as a
stable security master. Ticker identity must be supplied by an independent PIT
security-master source before normalized bars can enter the research universe.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import csv
from http.cookiejar import CookieJar
import io
import os
from typing import Callable, Mapping, Protocol
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import UUID
from zoneinfo import ZoneInfo

from ..contracts import DailyBar, DataQualityStatus
from ..errors import DataContractError
from ..time_utils import require_aware

NEW_YORK = ZoneInfo("America/New_York")


class KibotSchemaError(DataContractError):
    pass


class KibotLicenseError(PermissionError):
    pass


class KibotTransport(Protocol):
    def get_text(self, params: Mapping[str, str]) -> str: ...


class _UrllibKibotTransport:
    def __init__(self, base_url: str = "https://api.kibot.com/") -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.hostname != "api.kibot.com":
            raise ValueError("Kibot base_url must be https://api.kibot.com/")
        self.base_url = base_url
        self._opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def get_text(self, params: Mapping[str, str]) -> str:
        url = self.base_url + "?" + urlencode(dict(params))
        request = Request(url, headers={"Accept": "text/plain", "User-Agent": "quant-trading-bot/0.2"})
        with self._opener.open(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="strict")


@dataclass(frozen=True, slots=True)
class KibotMinuteBar:
    symbol: str
    interval_start: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "interval_start", require_aware(self.interval_start, "interval_start"))
        if not self.symbol.strip():
            raise KibotSchemaError("symbol is required")
        if any(x <= 0 for x in (self.open, self.high, self.low, self.close)):
            raise KibotSchemaError("OHLC must be positive")
        if self.high < max(self.open, self.close, self.low) or self.low > min(self.open, self.close, self.high):
            raise KibotSchemaError("invalid OHLC relationship")
        if self.volume < 0:
            raise KibotSchemaError("volume cannot be negative")


@dataclass(frozen=True, slots=True)
class KibotTrade:
    symbol: str
    observed_at: datetime
    price: Decimal
    size: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", require_aware(self.observed_at, "observed_at"))
        if not self.symbol.strip() or self.price <= 0 or self.size <= 0:
            raise KibotSchemaError("valid symbol, positive price, and positive size are required")


@dataclass(frozen=True, slots=True)
class KibotAdjustment:
    action_date: date
    symbol: str
    company: str
    action: str
    description: str

    def __post_init__(self) -> None:
        if self.action not in {"Split", "Reverse Split", "Dividend"}:
            raise KibotSchemaError(f"unsupported Kibot adjustment type {self.action!r}")
        if not self.symbol.strip() or not self.description.strip():
            raise KibotSchemaError("adjustment symbol and description are required")


class KibotClient:
    adapter_version = "KIBOT-HISTORICAL-v0.2.0"

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        transport: KibotTransport | None = None,
        license_approved: bool | None = None,
        allow_guest_evaluation: bool = False,
    ) -> None:
        self.username = username or os.getenv("KIBOT_USERNAME")
        self.password = password or os.getenv("KIBOT_PASSWORD")
        env_approved = os.getenv("KIBOT_PRIVATE_RESEARCH_LICENSE_APPROVED", "").strip().lower() in {"1", "true", "yes"}
        self.license_approved = env_approved if license_approved is None else license_approved
        self.allow_guest_evaluation = allow_guest_evaluation
        if not self.username or not self.password:
            if allow_guest_evaluation:
                self.username = "guest"
                self.password = "guest"
            else:
                raise ValueError("KIBOT_USERNAME and KIBOT_PASSWORD are required")
        self._guest = self.username == "guest"
        if not self._guest and not self.license_approved:
            raise KibotLicenseError("Kibot private research license approval flag is required")
        self._transport = transport or _UrllibKibotTransport()
        self._logged_in = False

    def login(self) -> str:
        text = self._transport.get_text({"action": "login", "user": self.username, "password": self.password})
        if not text.lstrip().startswith("200"):
            raise KibotSchemaError("Kibot login did not return 200 OK")
        self._logged_in = True
        return text

    def _ensure_login(self) -> None:
        if not self._logged_in:
            self.login()

    def history(
        self,
        symbol: str,
        *,
        interval: str,
        start: date | None = None,
        end: date | None = None,
        unadjusted: bool = True,
        regular_session: bool | None = None,
    ) -> str:
        if not symbol.strip():
            raise ValueError("symbol is required")
        self._ensure_login()
        params: dict[str, str] = {"action": "history", "symbol": symbol, "interval": interval}
        if start is not None:
            params["startdate"] = start.strftime("%m/%d/%Y")
        if end is not None:
            params["enddate"] = end.strftime("%m/%d/%Y")
        if unadjusted:
            params["unadjusted"] = "1"
        if regular_session is not None:
            params["regularsession"] = "1" if regular_session else "0"
        return self._transport.get_text(params)

    def adjustments(self, *, symbol: str, start: date | None = None, end: date | None = None) -> str:
        self._ensure_login()
        params = {"action": "adjustments", "symbol": symbol}
        if start is not None:
            params["startdate"] = start.strftime("%m/%d/%Y")
        if end is not None:
            params["enddate"] = end.strftime("%m/%d/%Y")
        return self._transport.get_text(params)


def _decimal(value: str) -> Decimal:
    try:
        result = Decimal(value.strip())
    except (InvalidOperation, ValueError) as exc:
        raise KibotSchemaError(f"invalid decimal {value!r}") from exc
    if not result.is_finite():
        raise KibotSchemaError("non-finite numeric value")
    return result


def _date(value: str) -> date:
    try:
        return datetime.strptime(value.strip(), "%m/%d/%Y").date()
    except ValueError as exc:
        raise KibotSchemaError(f"invalid Kibot date {value!r}") from exc


def parse_daily_history(text: str) -> tuple[tuple[date, Decimal, Decimal, Decimal, Decimal, int], ...]:
    rows = []
    seen: set[date] = set()
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        if len(row) != 6:
            raise KibotSchemaError("daily history rows must have six fields")
        d = _date(row[0])
        if d in seen:
            raise KibotSchemaError(f"duplicate daily bar {d}")
        seen.add(d)
        volume = int(row[5])
        if volume < 0:
            raise KibotSchemaError("volume cannot be negative")
        rows.append((d, _decimal(row[1]), _decimal(row[2]), _decimal(row[3]), _decimal(row[4]), volume))
    if not rows:
        raise KibotSchemaError("empty Kibot daily history")
    return tuple(sorted(rows, key=lambda x: x[0]))


def normalize_daily_history(
    text: str,
    *,
    instrument_id: UUID,
    source_snapshot_id: str,
    session_close_at: Callable[[date], datetime],
    publication_delay: timedelta = timedelta(hours=16),
) -> tuple[DailyBar, ...]:
    """Normalize unadjusted Kibot daily history.

    The conservative default availability is the next morning rather than
    close+30m because Kibot documents historical-update readiness before 8 AM ET,
    not a guaranteed 16:30 same-day publication SLA.
    """
    if publication_delay < timedelta(0):
        raise ValueError("publication_delay cannot be negative")
    result = []
    for d, o, h, l, c, v in parse_daily_history(text):
        observed = require_aware(session_close_at(d), "session_close_at")
        result.append(DailyBar(
            instrument_id=instrument_id,
            session_date=d,
            open=o, high=h, low=l, close=c, volume=v,
            observed_at=observed,
            available_at=observed + publication_delay,
            snapshot_id=source_snapshot_id,
            provider_revision=0,
            quality_status=DataQualityStatus.VALID,
        ))
    return tuple(result)


def parse_minute_history(text: str, *, symbol: str) -> tuple[KibotMinuteBar, ...]:
    result = []
    seen: set[datetime] = set()
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        if len(row) != 7:
            raise KibotSchemaError("minute history rows must have seven fields")
        try:
            local = datetime.strptime(f"{row[0].strip()} {row[1].strip()}", "%m/%d/%Y %H:%M:%S")
        except ValueError:
            try:
                local = datetime.strptime(f"{row[0].strip()} {row[1].strip()}", "%m/%d/%Y %H:%M")
            except ValueError as exc:
                raise KibotSchemaError("invalid Kibot minute timestamp") from exc
        observed = local.replace(tzinfo=NEW_YORK)
        if observed in seen:
            raise KibotSchemaError(f"duplicate minute bar {observed.isoformat()}")
        seen.add(observed)
        result.append(KibotMinuteBar(
            symbol=symbol,
            interval_start=observed,
            open=_decimal(row[2]), high=_decimal(row[3]), low=_decimal(row[4]), close=_decimal(row[5]),
            volume=int(row[6]),
        ))
    if not result:
        raise KibotSchemaError("empty Kibot minute history")
    return tuple(sorted(result, key=lambda x: x.interval_start))


def parse_tick_history(text: str, *, symbol: str) -> tuple[KibotTrade, ...]:
    result = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        if len(row) not in {4, 6, 9}:
            raise KibotSchemaError("unsupported Kibot tick schema")
        try:
            local = datetime.strptime(f"{row[0].strip()} {row[1].strip()}", "%m/%d/%Y %H:%M:%S")
        except ValueError as exc:
            raise KibotSchemaError("invalid Kibot tick timestamp") from exc
        # 4-field: date,time,price,size; 6-field: date,time,price,bid,ask,size
        size_index = 3 if len(row) == 4 else 5
        result.append(KibotTrade(symbol=symbol, observed_at=local.replace(tzinfo=NEW_YORK), price=_decimal(row[2]), size=int(row[size_index])))
    if not result:
        raise KibotSchemaError("empty Kibot tick history")
    return tuple(result)


def exact_trade_vwap(
    trades: tuple[KibotTrade, ...],
    *,
    session_date: date,
    start_time: time = time(10, 0),
    end_time: time = time(10, 30),
) -> Decimal:
    selected = [t for t in trades if t.observed_at.astimezone(NEW_YORK).date() == session_date and start_time <= t.observed_at.astimezone(NEW_YORK).time().replace(tzinfo=None) < end_time]
    if not selected:
        raise KibotSchemaError("no trades in execution VWAP window")
    total_size = sum(t.size for t in selected)
    if total_size <= 0:
        raise KibotSchemaError("execution VWAP has no positive size")
    return sum((t.price * t.size for t in selected), Decimal("0")) / Decimal(total_size)


def parse_adjustments(text: str) -> tuple[KibotAdjustment, ...]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ()
    reader = csv.reader(lines, delimiter="\t")
    header = next(reader)
    expected = ["Date", "Symbol", "Company", "Action", "Description"]
    if [x.strip() for x in header] != expected:
        raise KibotSchemaError("unexpected Kibot adjustment header")
    result = []
    for row in reader:
        if len(row) != 5:
            raise KibotSchemaError("adjustment rows must have five fields")
        result.append(KibotAdjustment(_date(row[0]), row[1].strip(), row[2].strip(), row[3].strip(), row[4].strip()))
    return tuple(result)

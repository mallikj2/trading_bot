"""Provider-adapter contracts that sit immediately above the Phase 02 kernel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping, Any
from uuid import UUID

from ..contracts import DataQualityStatus
from ..errors import DataContractError
from ..time_utils import require_aware


class AvailabilitySemantics(str, Enum):
    """How a provider field may be used in historical research."""

    PROVIDER_TIMESTAMP = "PROVIDER_TIMESTAMP"
    EFFECTIVE_DATE_CONSERVATIVE = "EFFECTIVE_DATE_CONSERVATIVE"
    RETRIEVAL_ONLY = "RETRIEVAL_ONLY"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class TickerReference:
    ticker: str
    name: str
    primary_exchange_mic: str
    ticker_type: str
    active: bool
    as_of_date: date
    available_at: datetime
    source_snapshot_id: str
    cik: str | None = None
    composite_figi: str | None = None
    share_class_figi: str | None = None
    delisted_date: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "available_at", require_aware(self.available_at, "available_at"))
        required = (self.ticker, self.name, self.primary_exchange_mic, self.ticker_type, self.source_snapshot_id)
        if any(not value.strip() for value in required):
            raise DataContractError("ticker reference identity fields are required")
        if not any((self.cik, self.composite_figi, self.share_class_figi)):
            raise DataContractError("ticker reference requires at least one stable identifier")


@dataclass(frozen=True, slots=True)
class IntradayBar:
    instrument_id: UUID
    symbol: str
    session_date: date
    interval_start: datetime
    interval_end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Decimal
    available_at: datetime
    source_snapshot_id: str
    provider_revision: int = 0
    quality_status: DataQualityStatus = DataQualityStatus.VALID

    def __post_init__(self) -> None:
        start = require_aware(self.interval_start, "interval_start")
        end = require_aware(self.interval_end, "interval_end")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "interval_start", start)
        object.__setattr__(self, "interval_end", end)
        object.__setattr__(self, "available_at", available)
        if end <= start:
            raise DataContractError("intraday interval_end must follow interval_start")
        if available < end:
            raise DataContractError("intraday available_at cannot precede interval_end")
        prices = (self.open, self.high, self.low, self.close, self.vwap)
        if any(value <= 0 for value in prices):
            raise DataContractError("intraday OHLC/VWAP values must be positive")
        if self.high < max(self.open, self.close, self.low):
            raise DataContractError("intraday high violates OHLC relationship")
        if self.low > min(self.open, self.close, self.high):
            raise DataContractError("intraday low violates OHLC relationship")
        if self.volume < 0:
            raise DataContractError("intraday volume cannot be negative")
        if not self.symbol.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("intraday symbol and source_snapshot_id are required")
        if self.provider_revision < 0:
            raise DataContractError("provider_revision cannot be negative")


@dataclass(frozen=True, slots=True)
class SharesOutstandingObservation:
    instrument_id: UUID
    period_end: date
    shares_outstanding: Decimal
    accession_number: str
    form_type: str
    filed_date: date
    accepted_at: datetime
    available_at: datetime
    source_snapshot_id: str
    concept: str
    taxonomy: str
    revision: int = 0

    def __post_init__(self) -> None:
        accepted = require_aware(self.accepted_at, "accepted_at")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "accepted_at", accepted)
        object.__setattr__(self, "available_at", available)
        if available < accepted:
            raise DataContractError("shares available_at cannot precede SEC acceptance")
        if self.shares_outstanding <= 0:
            raise DataContractError("shares_outstanding must be positive")
        required = (
            self.accession_number,
            self.form_type,
            self.source_snapshot_id,
            self.concept,
            self.taxonomy,
        )
        if any(not value.strip() for value in required):
            raise DataContractError("shares observation identity fields are required")
        if self.revision < 0:
            raise DataContractError("revision cannot be negative")


@dataclass(frozen=True, slots=True)
class CurrentSicReference:
    """Current-only SEC SIC metadata; intentionally not a PIT sector observation."""

    cik: str
    sic_code: str
    sic_description: str
    retrieved_at: datetime
    source_snapshot_id: str
    historical_use_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "retrieved_at", require_aware(self.retrieved_at, "retrieved_at"))
        if not self.cik.strip() or not self.sic_code.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("current SIC reference fields are required")
        if self.historical_use_allowed:
            raise DataContractError("SEC submissions SIC cannot be promoted to historical sector data")


@dataclass(frozen=True, slots=True)
class SnapshotReceipt:
    snapshot_id: str
    snapshot_root: str
    payload_path: str
    manifest_path: str
    manifest_hash: str
    record_count: int


@dataclass(frozen=True, slots=True)
class TrialCheck:
    check_id: str
    status: str
    detail: str
    evidence: Mapping[str, Any]

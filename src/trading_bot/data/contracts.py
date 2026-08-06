"""Typed data contracts for Phase 02 point-in-time research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping
from uuid import UUID

from .errors import DataContractError
from .time_utils import require_aware


class DataQualityStatus(str, Enum):
    VALID = "VALID"
    SUSPECT = "SUSPECT"
    REJECTED = "REJECTED"


class SecurityType(str, Enum):
    COMMON_STOCK = "COMMON_STOCK"
    ETF = "ETF"
    PREFERRED = "PREFERRED"
    WARRANT = "WARRANT"
    RIGHT = "RIGHT"
    UNIT = "UNIT"
    CLOSED_END_FUND = "CLOSED_END_FUND"
    OTHER = "OTHER"


class ListingState(str, Enum):
    LISTED = "LISTED"
    HALTED = "HALTED"
    SUSPENDED = "SUSPENDED"
    DELISTED = "DELISTED"
    INACTIVE = "INACTIVE"


class CorporateActionType(str, Enum):
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    SPINOFF = "SPINOFF"
    MERGER = "MERGER"
    ACQUISITION = "ACQUISITION"
    TENDER_OFFER = "TENDER_OFFER"
    RIGHTS_DISTRIBUTION = "RIGHTS_DISTRIBUTION"
    BANKRUPTCY = "BANKRUPTCY"
    LIQUIDATION = "LIQUIDATION"
    SYMBOL_CHANGE = "SYMBOL_CHANGE"
    DELISTING = "DELISTING"
    RELISTING = "RELISTING"


class CorporateActionStatus(str, Enum):
    ANNOUNCED = "ANNOUNCED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EarningsTiming(str, Enum):
    BMO = "BMO"
    AMC = "AMC"
    DURING_SESSION = "DURING_SESSION"
    UNKNOWN = "UNKNOWN"


class UniverseReason(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_LISTED = "NOT_LISTED"
    WRONG_EXCHANGE = "WRONG_EXCHANGE"
    WRONG_SECURITY_TYPE = "WRONG_SECURITY_TYPE"
    PRICE_TOO_LOW = "PRICE_TOO_LOW"
    MARKET_CAP_TOO_LOW = "MARKET_CAP_TOO_LOW"
    INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    VOLATILITY_TOO_HIGH = "VOLATILITY_TOO_HIGH"
    MISSING_SECTOR = "MISSING_SECTOR"
    DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"
    CORPORATE_ACTION_UNRESOLVED = "CORPORATE_ACTION_UNRESOLVED"
    UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"
    FUTURE_INFORMATION = "FUTURE_INFORMATION"


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_id: UUID
    security_type: SecurityType
    currency: str
    country_of_listing: str
    created_at: datetime
    issuer_id: UUID | None = None
    cik: str | None = None
    retired_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", require_aware(self.created_at, "created_at"))
        if self.retired_at is not None:
            retired = require_aware(self.retired_at, "retired_at")
            if retired <= self.created_at:
                raise DataContractError("retired_at must be later than created_at")
            object.__setattr__(self, "retired_at", retired)
        if not self.currency.strip() or not self.country_of_listing.strip():
            raise DataContractError("currency and country_of_listing are required")


@dataclass(frozen=True, slots=True)
class SymbolAlias:
    instrument_id: UUID
    symbol: str
    exchange: str
    valid_from: datetime
    valid_to: datetime | None
    provider_symbol: str
    source_snapshot_id: str
    mapping_reason: str
    available_at: datetime

    def __post_init__(self) -> None:
        if not self.symbol.strip() or not self.exchange.strip():
            raise DataContractError("symbol and exchange are required")
        if not self.provider_symbol.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("provider_symbol and source_snapshot_id are required")
        start = require_aware(self.valid_from, "valid_from")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "valid_from", start)
        object.__setattr__(self, "available_at", available)
        if self.valid_to is not None:
            end = require_aware(self.valid_to, "valid_to")
            if end <= start:
                raise DataContractError("valid_to must be later than valid_from")
            object.__setattr__(self, "valid_to", end)


@dataclass(frozen=True, slots=True)
class DailyBar:
    instrument_id: UUID
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    observed_at: datetime
    available_at: datetime
    snapshot_id: str
    provider_revision: int = 0
    quality_status: DataQualityStatus = DataQualityStatus.VALID

    def __post_init__(self) -> None:
        observed = require_aware(self.observed_at, "observed_at")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "available_at", available)
        if observed.date() < self.session_date:
            raise DataContractError("observed_at cannot precede session_date")
        if available < observed:
            raise DataContractError("available_at cannot precede observed_at for a daily bar")
        prices = (self.open, self.high, self.low, self.close)
        if any(value <= 0 for value in prices):
            raise DataContractError("OHLC prices must be positive")
        if self.high < max(self.open, self.close, self.low):
            raise DataContractError("high violates OHLC relationship")
        if self.low > min(self.open, self.close, self.high):
            raise DataContractError("low violates OHLC relationship")
        if self.volume < 0:
            raise DataContractError("volume cannot be negative")
        if self.provider_revision < 0:
            raise DataContractError("provider_revision cannot be negative")
        if not self.snapshot_id.strip():
            raise DataContractError("snapshot_id is required")


@dataclass(frozen=True, slots=True)
class CorporateAction:
    action_id: str
    instrument_id: UUID
    action_type: CorporateActionType
    effective_at: datetime
    available_at: datetime
    source_snapshot_id: str
    revision: int = 0
    split_new_shares: Decimal | None = None
    split_old_shares: Decimal | None = None
    cash_amount: Decimal | None = None
    currency: str | None = None
    stock_ratio: Decimal | None = None
    child_instrument_id: UUID | None = None
    successor_instrument_id: UUID | None = None
    announced_at: datetime | None = None
    status: CorporateActionStatus = CorporateActionStatus.CONFIRMED
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_id.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("action_id and source_snapshot_id are required")
        effective = require_aware(self.effective_at, "effective_at")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "effective_at", effective)
        object.__setattr__(self, "available_at", available)
        if self.revision < 0:
            raise DataContractError("revision cannot be negative")
        if self.action_type in {CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT}:
            if self.split_new_shares is None or self.split_old_shares is None:
                raise DataContractError("split actions require new and old share quantities")
            if self.split_new_shares <= 0 or self.split_old_shares <= 0:
                raise DataContractError("split quantities must be positive")
        if self.announced_at is not None:
            announced = require_aware(self.announced_at, "announced_at")
            object.__setattr__(self, "announced_at", announced)
        if self.action_type == CorporateActionType.CASH_DIVIDEND:
            if self.cash_amount is None or self.cash_amount < 0:
                raise DataContractError("cash dividends require a non-negative cash amount")
            if not self.currency:
                raise DataContractError("cash dividends require currency")
        if self.action_type == CorporateActionType.STOCK_DIVIDEND:
            if self.stock_ratio is None or self.stock_ratio <= 0:
                raise DataContractError("stock dividends require a positive stock_ratio")
        if self.action_type == CorporateActionType.SPINOFF:
            if self.stock_ratio is None or self.stock_ratio <= 0:
                raise DataContractError("spinoffs require a positive stock_ratio")
            if self.child_instrument_id is None:
                raise DataContractError("spinoffs require child_instrument_id")
        if self.action_type in {CorporateActionType.MERGER, CorporateActionType.ACQUISITION}:
            if self.cash_amount is None and self.stock_ratio is None:
                raise DataContractError("merger/acquisition requires cash or stock consideration")
            if self.stock_ratio is not None and self.stock_ratio < 0:
                raise DataContractError("stock consideration ratio cannot be negative")
            if self.stock_ratio and self.successor_instrument_id is None:
                raise DataContractError("stock consideration requires successor_instrument_id")
        if self.action_type in {
            CorporateActionType.DELISTING,
            CorporateActionType.LIQUIDATION,
            CorporateActionType.BANKRUPTCY,
        } and self.cash_amount is not None and self.cash_amount < 0:
            raise DataContractError("terminal cash consideration cannot be negative")
        if self.cash_amount is not None and self.currency is None:
            raise DataContractError("cash-bearing corporate actions require currency")


@dataclass(frozen=True, slots=True)
class ListingStatus:
    instrument_id: UUID
    exchange: str
    state: ListingState
    effective_from: datetime
    effective_to: datetime | None
    available_at: datetime
    source_snapshot_id: str
    reason: str | None = None

    def __post_init__(self) -> None:
        start = require_aware(self.effective_from, "effective_from")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "effective_from", start)
        object.__setattr__(self, "available_at", available)
        if self.effective_to is not None:
            end = require_aware(self.effective_to, "effective_to")
            if end <= start:
                raise DataContractError("effective_to must be later than effective_from")
            object.__setattr__(self, "effective_to", end)
        if not self.exchange.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("exchange and source_snapshot_id are required")


@dataclass(frozen=True, slots=True)
class MarketCapObservation:
    instrument_id: UUID
    observed_at: datetime
    available_at: datetime
    market_cap: Decimal
    source_snapshot_id: str
    revision: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", require_aware(self.observed_at, "observed_at"))
        object.__setattr__(self, "available_at", require_aware(self.available_at, "available_at"))
        if self.market_cap <= 0:
            raise DataContractError("market_cap must be positive")
        if self.revision < 0:
            raise DataContractError("revision cannot be negative")


@dataclass(frozen=True, slots=True)
class SectorObservation:
    instrument_id: UUID
    taxonomy_id: str
    taxonomy_version: str
    sector_code: str
    sector_label: str
    effective_from: datetime
    effective_to: datetime | None
    available_at: datetime
    source_snapshot_id: str
    revision: int = 0

    def __post_init__(self) -> None:
        start = require_aware(self.effective_from, "effective_from")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "effective_from", start)
        object.__setattr__(self, "available_at", available)
        if self.effective_to is not None:
            end = require_aware(self.effective_to, "effective_to")
            if end <= start:
                raise DataContractError("effective_to must be later than effective_from")
            object.__setattr__(self, "effective_to", end)
        required = (self.taxonomy_id, self.taxonomy_version, self.sector_code, self.sector_label)
        if any(not value.strip() for value in required):
            raise DataContractError("sector taxonomy fields are required")
        if self.revision < 0:
            raise DataContractError("revision cannot be negative")


@dataclass(frozen=True, slots=True)
class EarningsSchedule:
    event_id: str
    instrument_id: UUID
    scheduled_session: date
    timing: EarningsTiming
    available_at: datetime
    source_snapshot_id: str
    revision: int
    status: str = "SCHEDULED"

    def __post_init__(self) -> None:
        object.__setattr__(self, "available_at", require_aware(self.available_at, "available_at"))
        if not self.event_id.strip() or not self.source_snapshot_id.strip():
            raise DataContractError("event_id and source_snapshot_id are required")
        if self.revision < 0:
            raise DataContractError("revision cannot be negative")


@dataclass(frozen=True, slots=True)
class ExchangeSession:
    calendar_id: str
    calendar_version: str
    session_date: date
    open_at: datetime
    close_at: datetime
    early_close: bool = False

    def __post_init__(self) -> None:
        open_at = require_aware(self.open_at, "open_at")
        close_at = require_aware(self.close_at, "close_at")
        object.__setattr__(self, "open_at", open_at)
        object.__setattr__(self, "close_at", close_at)
        if close_at <= open_at:
            raise DataContractError("session close must be after session open")
        if not self.calendar_id.strip() or not self.calendar_version.strip():
            raise DataContractError("calendar identity and version are required")


@dataclass(frozen=True, slots=True)
class UniverseInput:
    instrument_id: UUID
    exchange: str | None
    security_type: SecurityType | None
    listing_state: ListingState | None
    adjusted_close: Decimal | None
    market_cap: Decimal | None
    adv60: Decimal | None
    valid_sessions: int | None
    vol20_annualized: Decimal | None
    sector_code: str | None
    quality_status: DataQualityStatus
    unresolved_corporate_action: bool
    identity_resolved: bool
    latest_available_at: datetime
    source_manifest_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "latest_available_at",
            require_aware(self.latest_available_at, "latest_available_at"),
        )
        if not self.source_manifest_hashes:
            raise DataContractError("source_manifest_hashes cannot be empty")


@dataclass(frozen=True, slots=True)
class UniverseMembership:
    universe_version: str
    effective_month: date
    instrument_id: UUID
    eligible: bool
    reason_codes: tuple[UniverseReason, ...]
    freeze_at: datetime
    source_manifest_hash: str
    calculation_version: str
    frozen_values_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "freeze_at", require_aware(self.freeze_at, "freeze_at"))
        if self.effective_month.day != 1:
            raise DataContractError("effective_month must be the first day of a month")
        if not self.reason_codes:
            raise DataContractError("reason_codes cannot be empty")
        if self.eligible and self.reason_codes != (UniverseReason.ELIGIBLE,):
            raise DataContractError("eligible rows must contain only ELIGIBLE")
        if not self.eligible and UniverseReason.ELIGIBLE in self.reason_codes:
            raise DataContractError("ineligible rows cannot contain ELIGIBLE")


@dataclass(frozen=True, slots=True)
class FeatureObservation:
    feature_name: str
    feature_version: str
    instrument_id: UUID
    observed_at: datetime
    available_at: datetime
    value: Decimal | None
    input_manifest_hashes: tuple[str, ...]
    formula_hash: str
    universe_version: str | None = None
    null_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", require_aware(self.observed_at, "observed_at"))
        object.__setattr__(self, "available_at", require_aware(self.available_at, "available_at"))
        if not self.feature_name.strip() or not self.feature_version.strip():
            raise DataContractError("feature identity is required")
        if not self.input_manifest_hashes or not self.formula_hash.strip():
            raise DataContractError("feature lineage is required")
        if self.value is None and not self.null_reason:
            raise DataContractError("null feature values require null_reason")

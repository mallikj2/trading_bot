"""Production provider adapters for Phase 02 research ingestion."""

from .massive import (
    MassiveClient,
    MassiveSchemaError,
    normalize_daily_bars,
    normalize_dividends,
    normalize_intraday_bars,
    normalize_overview_market_cap,
    normalize_overview_sector,
    normalize_splits,
    normalize_ticker_events,
    normalize_ticker_references,
)
from .models import (
    AvailabilitySemantics,
    CurrentSicReference,
    IntradayBar,
    SharesOutstandingObservation,
    SnapshotReceipt,
    TickerReference,
)
from .sec_edgar import (
    SecEdgarClient,
    SecSchemaError,
    build_accession_acceptance_map,
    derive_market_cap,
    extract_current_sic_reference,
    extract_shares_outstanding,
    historical_sector_from_submissions,
    select_shares_as_of,
)
from .storage import RawSnapshotStore
from .vwap import ExecutionVwap, build_execution_vwap

__all__ = [
    "MassiveClient",
    "MassiveSchemaError",
    "SecEdgarClient",
    "SecSchemaError",
    "RawSnapshotStore",
    "TickerReference",
    "IntradayBar",
    "SharesOutstandingObservation",
    "CurrentSicReference",
    "SnapshotReceipt",
    "AvailabilitySemantics",
    "ExecutionVwap",
    "normalize_ticker_references",
    "normalize_daily_bars",
    "normalize_intraday_bars",
    "normalize_splits",
    "normalize_dividends",
    "normalize_overview_market_cap",
    "normalize_overview_sector",
    "normalize_ticker_events",
    "build_accession_acceptance_map",
    "extract_shares_outstanding",
    "select_shares_as_of",
    "derive_market_cap",
    "extract_current_sic_reference",
    "historical_sector_from_submissions",
    "build_execution_vwap",
]

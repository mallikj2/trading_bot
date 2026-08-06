"""Phase 02 minimum data kernel."""

from .calendars import ExchangeCalendar
from .contracts import *  # noqa: F403
from .corporate_actions import adjusted_close_as_of, split_adjustment_factor
from .identity import InstrumentMaster
from .leakage import assert_lineage_hashes, assert_no_future_information
from .manifests import DatasetManifest, SourceFile
from .pit import derive_feature_available_at, select_latest_known
from .universe import UniversePolicy, build_monthly_universe, universe_membership_hash
from .total_returns import (
    ActionValuationMethod,
    ActionValuationPurpose,
    CorporateActionCoverage,
    CorporateActionValuation,
    TotalReturnBuild,
    apply_actions_to_position_as_of,
    build_total_return_as_of,
    continuing_event_backward_factor,
    continuing_event_gross_return,
    continuing_event_value,
)
from .strategy_inputs import StrategyPriceRecord, strategy_price_records

__all__ = [
    "ExchangeCalendar",
    "InstrumentMaster",
    "DatasetManifest",
    "SourceFile",
    "UniversePolicy",
    "adjusted_close_as_of",
    "split_adjustment_factor",
    "assert_lineage_hashes",
    "assert_no_future_information",
    "derive_feature_available_at",
    "select_latest_known",
    "build_monthly_universe",
    "universe_membership_hash",
    "ActionValuationMethod",
    "ActionValuationPurpose",
    "CorporateActionCoverage",
    "CorporateActionValuation",
    "TotalReturnBuild",
    "apply_actions_to_position_as_of",
    "build_total_return_as_of",
    "continuing_event_backward_factor",
    "continuing_event_gross_return",
    "continuing_event_value",
    "StrategyPriceRecord",
    "strategy_price_records",
]

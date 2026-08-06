"""Deterministic monthly universe freezing for CSMOM-LS-v0.2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from .contracts import (
    DataQualityStatus,
    ListingState,
    SecurityType,
    UniverseInput,
    UniverseMembership,
    UniverseReason,
)
from .errors import UniverseBuildError
from .hashing import content_hash
from .time_utils import require_aware


@dataclass(frozen=True, slots=True)
class UniversePolicy:
    policy_version: str = "CSMOM-LS-v0.2-UNIVERSE-v0.1"
    allowed_exchanges: tuple[str, ...] = ("NYSE", "NASDAQ")
    required_security_type: SecurityType = SecurityType.COMMON_STOCK
    min_adjusted_close: Decimal = Decimal("10")
    min_market_cap: Decimal = Decimal("2000000000")
    min_adv60: Decimal = Decimal("25000000")
    min_valid_sessions: int = 300
    max_vol20_annualized: Decimal = Decimal("0.80")


def _reasons(value: UniverseInput, freeze_at: datetime, policy: UniversePolicy) -> tuple[UniverseReason, ...]:
    reasons: list[UniverseReason] = []
    if value.latest_available_at > freeze_at:
        reasons.append(UniverseReason.FUTURE_INFORMATION)
    if not value.identity_resolved:
        reasons.append(UniverseReason.UNKNOWN_IDENTITY)
    if value.exchange not in policy.allowed_exchanges:
        reasons.append(UniverseReason.WRONG_EXCHANGE)
    if value.security_type != policy.required_security_type:
        reasons.append(UniverseReason.WRONG_SECURITY_TYPE)
    if value.listing_state != ListingState.LISTED:
        reasons.append(UniverseReason.NOT_LISTED)
    if value.adjusted_close is None or value.adjusted_close < policy.min_adjusted_close:
        reasons.append(UniverseReason.PRICE_TOO_LOW)
    if value.market_cap is None or value.market_cap < policy.min_market_cap:
        reasons.append(UniverseReason.MARKET_CAP_TOO_LOW)
    if value.adv60 is None or value.adv60 < policy.min_adv60:
        reasons.append(UniverseReason.INSUFFICIENT_LIQUIDITY)
    if value.valid_sessions is None or value.valid_sessions < policy.min_valid_sessions:
        reasons.append(UniverseReason.INSUFFICIENT_HISTORY)
    if value.vol20_annualized is None or value.vol20_annualized > policy.max_vol20_annualized:
        reasons.append(UniverseReason.VOLATILITY_TOO_HIGH)
    if value.sector_code is None or not value.sector_code.strip():
        reasons.append(UniverseReason.MISSING_SECTOR)
    if value.quality_status != DataQualityStatus.VALID:
        reasons.append(UniverseReason.DATA_QUALITY_FAILURE)
    if value.unresolved_corporate_action:
        reasons.append(UniverseReason.CORPORATE_ACTION_UNRESOLVED)
    return tuple(dict.fromkeys(reasons))


def build_monthly_universe(
    inputs: Iterable[UniverseInput],
    *,
    effective_month: date,
    freeze_at: datetime,
    source_manifest_hash: str,
    universe_version: str,
    policy: UniversePolicy | None = None,
) -> tuple[UniverseMembership, ...]:
    """Freeze deterministic membership and complete reason codes for a month."""
    if effective_month.day != 1:
        raise UniverseBuildError("effective_month must be the first day of a month")
    freeze = require_aware(freeze_at, "freeze_at")
    if len(source_manifest_hash) != 64:
        raise UniverseBuildError("source_manifest_hash must be SHA-256")
    cfg = policy or UniversePolicy()
    rows = sorted(inputs, key=lambda item: item.instrument_id.hex)
    if not rows:
        raise UniverseBuildError("universe input is empty")
    if len({row.instrument_id for row in rows}) != len(rows):
        raise UniverseBuildError("duplicate instrument in universe input")

    memberships: list[UniverseMembership] = []
    for row in rows:
        reasons = _reasons(row, freeze, cfg)
        eligible = not reasons
        frozen_hash = content_hash(row)
        memberships.append(
            UniverseMembership(
                universe_version=universe_version,
                effective_month=effective_month,
                instrument_id=row.instrument_id,
                eligible=eligible,
                reason_codes=(UniverseReason.ELIGIBLE,) if eligible else reasons,
                freeze_at=freeze,
                source_manifest_hash=source_manifest_hash,
                calculation_version=cfg.policy_version,
                frozen_values_hash=frozen_hash,
            )
        )
    return tuple(memberships)


def universe_membership_hash(memberships: Iterable[UniverseMembership]) -> str:
    ordered = sorted(memberships, key=lambda row: row.instrument_id.hex)
    return content_hash(ordered)

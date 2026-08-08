"""Integration primitives for the final PIT identity/execution evidence gates.

This module turns the approved Phase 01 universe rules into a *sector-blind*
monthly target ledger.  It deliberately uses the same UniverseInput contract as
the final universe and removes only the sector requirement.  Therefore the SEC
sector coverage denominator cannot be improved by filtering away missing sector
records.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import json
from pathlib import Path
from typing import Iterable, Mapping
from uuid import UUID

from .adapters.databento_companion import DatabentoPitListing, select_primary_listing_as_of
from .contracts import DailyBar, ListingState, MarketCapObservation, SecurityType, UniverseInput, UniverseMembership
from .errors import DataContractError, PointInTimeError
from .sector_coverage import SectorCoverageRequirement
from .time_utils import require_aware
from .universe import UniversePolicy, build_sector_blind_monthly_universe


class PitAcceptanceError(DataContractError):
    pass


@dataclass(frozen=True, slots=True)
class SectorBlindLedgerBuild:
    effective_month: date
    freeze_at: datetime
    universe_version: str
    source_manifest_hash: str
    membership_count: int
    eligible_count: int
    rows: tuple[SectorCoverageRequirement, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "freeze_at", require_aware(self.freeze_at, "freeze_at"))
        if self.effective_month.day != 1:
            raise PitAcceptanceError("effective_month must be first day of month")
        if self.eligible_count != len(self.rows):
            raise PitAcceptanceError("eligible_count must equal target-ledger row count")


def _inputs_by_id(inputs: Iterable[UniverseInput]) -> dict[UUID, UniverseInput]:
    rows: dict[UUID, UniverseInput] = {}
    for row in inputs:
        if row.instrument_id in rows:
            raise PitAcceptanceError("duplicate UniverseInput instrument")
        rows[row.instrument_id] = row
    if not rows:
        raise PitAcceptanceError("sector-blind ledger requires universe inputs")
    return rows



def derive_market_cap_from_pit_listing(
    *,
    listing: DatabentoPitListing,
    raw_close_bar: DailyBar,
    decision_at: datetime,
    source_snapshot_id: str,
) -> MarketCapObservation:
    """Derive market cap from a PIT security-master share count and raw close.

    This is an alternate/corroborating market-cap path to SEC company-facts. It
    is only valid when the provider record, share-count effective date and raw
    close were all known by the decision timestamp.
    """
    decision = require_aware(decision_at, "decision_at")
    if listing.instrument_id != raw_close_bar.instrument_id:
        raise PitAcceptanceError("market-cap inputs reference different instruments")
    if listing.available_at > decision or raw_close_bar.available_at > decision:
        raise PointInTimeError("market-cap input was not available by decision_at")
    if listing.shares_outstanding is None or listing.shares_outstanding_date is None:
        raise PitAcceptanceError("PIT security-master record lacks shares outstanding")
    if listing.shares_outstanding_date > decision.date():
        raise PointInTimeError("shares_outstanding_date is in the future")
    return MarketCapObservation(
        instrument_id=listing.instrument_id,
        observed_at=raw_close_bar.observed_at,
        available_at=max(listing.available_at, raw_close_bar.available_at),
        market_cap=raw_close_bar.close * listing.shares_outstanding,
        source_snapshot_id=source_snapshot_id,
        revision=raw_close_bar.provider_revision,
    )

def build_sector_blind_target_ledger(
    inputs: Iterable[UniverseInput],
    *,
    listing_observations: Iterable[DatabentoPitListing],
    effective_month: date,
    freeze_at: datetime,
    source_manifest_hash: str,
    universe_version: str,
    policy: UniversePolicy | None = None,
) -> SectorBlindLedgerBuild:
    """Build the exact denominator needed by P02-G07.

    Every Phase 01 universe rule is applied except sector.  For each otherwise
    eligible instrument, a PIT primary-listing record must independently confirm
    identity, common-stock type, NYSE/Nasdaq listing, and CIK. Missing CIK is a
    hard upstream evidence failure rather than a silent exclusion from sector
    coverage.
    """
    freeze = require_aware(freeze_at, "freeze_at")
    by_id = _inputs_by_id(inputs)
    observations = tuple(listing_observations)
    memberships = build_sector_blind_monthly_universe(
        by_id.values(),
        effective_month=effective_month,
        freeze_at=freeze,
        source_manifest_hash=source_manifest_hash,
        universe_version=universe_version,
        policy=policy,
    )
    rows: list[SectorCoverageRequirement] = []
    for membership in memberships:
        if not membership.eligible:
            continue
        source = by_id[membership.instrument_id]
        listing = select_primary_listing_as_of(
            observations,
            instrument_id=membership.instrument_id,
            decision_at=freeze,
        )
        if listing.cik is None:
            raise PitAcceptanceError(
                f"otherwise-eligible instrument {membership.instrument_id} lacks PIT CIK"
            )
        if listing.exchange != source.exchange:
            raise PitAcceptanceError(
                f"universe/security-master exchange mismatch for {membership.instrument_id}: "
                f"{source.exchange!r} != {listing.exchange!r}"
            )
        if listing.security_type != SecurityType.COMMON_STOCK or source.security_type != SecurityType.COMMON_STOCK:
            raise PitAcceptanceError("otherwise-eligible target is not independently confirmed as common stock")
        if listing.listing_state != ListingState.LISTED or source.listing_state != ListingState.LISTED:
            raise PitAcceptanceError("otherwise-eligible target is not independently confirmed listed")
        rows.append(
            SectorCoverageRequirement(
                instrument_id=membership.instrument_id,
                cik=listing.cik,
                decision_at=freeze,
                source_manifest_hash=membership.source_manifest_hash,
                universe_version=membership.universe_version,
            )
        )
    if not rows:
        raise PitAcceptanceError("sector-blind universe produced zero eligible targets")
    return SectorBlindLedgerBuild(
        effective_month=effective_month,
        freeze_at=freeze,
        universe_version=universe_version,
        source_manifest_hash=source_manifest_hash,
        membership_count=len(memberships),
        eligible_count=len(rows),
        rows=tuple(sorted(rows, key=lambda row: row.instrument_id.hex)),
    )


def ledger_payload(builds: Iterable[SectorBlindLedgerBuild]) -> dict[str, object]:
    builds_tuple = tuple(builds)
    if not builds_tuple:
        raise PitAcceptanceError("at least one sector-blind ledger build is required")
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for build in sorted(builds_tuple, key=lambda item: item.freeze_at):
        for row in build.rows:
            key = (str(row.instrument_id), row.decision_at.isoformat())
            if key in seen:
                raise PitAcceptanceError("duplicate target-ledger instrument/decision point")
            seen.add(key)
            rows.append(
                {
                    "instrument_id": str(row.instrument_id),
                    "cik": row.cik,
                    "decision_at": row.decision_at.isoformat(),
                    "source_manifest_hash": row.source_manifest_hash,
                    "universe_version": row.universe_version,
                }
            )
    return {
        "version": "0.2.0",
        "sector_blind": True,
        "row_count": len(rows),
        "months": [build.effective_month.isoformat() for build in sorted(builds_tuple, key=lambda item: item.freeze_at)],
        "rows": rows,
    }


def write_sector_target_ledger(path: str | Path, builds: Iterable[SectorBlindLedgerBuild]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ledger_payload(builds), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def memberships_by_id(memberships: Iterable[UniverseMembership]) -> Mapping[UUID, UniverseMembership]:
    """Small validation helper used by credentialed evidence reports."""
    output: dict[UUID, UniverseMembership] = {}
    for row in memberships:
        if row.instrument_id in output:
            raise PitAcceptanceError("duplicate universe membership")
        output[row.instrument_id] = row
    return output

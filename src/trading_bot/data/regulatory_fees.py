"""Historical U.S. equity regulatory-fee basis for Phase 02/03.

The module models the official effective-dated Section 31 and FINRA Trading Activity
Fee (TAF) basis used for research cost attribution.  It does not claim to reproduce a
particular broker's historical customer invoice or rounding convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Sequence

from .costs import RegulatoryFeeScheduleEntry
from .errors import DataContractError, PointInTimeError


@dataclass(frozen=True, slots=True)
class Section31RateEntry:
    effective_from: date
    effective_to: date
    usd_per_million: Decimal
    source_reference: str

    def __post_init__(self) -> None:
        if self.effective_to < self.effective_from:
            raise DataContractError("Section 31 end date precedes start date")
        if self.usd_per_million < 0:
            raise DataContractError("Section 31 rate cannot be negative")
        if not self.source_reference.strip():
            raise DataContractError("Section 31 source reference is required")

    def covers(self, trade_date: date) -> bool:
        return self.effective_from <= trade_date <= self.effective_to


@dataclass(frozen=True, slots=True)
class FinraTafRateEntry:
    effective_from: date
    effective_to: date
    usd_per_share: Decimal
    maximum_usd_per_trade: Decimal
    source_reference: str

    def __post_init__(self) -> None:
        if self.effective_to < self.effective_from:
            raise DataContractError("FINRA TAF end date precedes start date")
        if self.usd_per_share < 0 or self.maximum_usd_per_trade < 0:
            raise DataContractError("FINRA TAF rates cannot be negative")
        if not self.source_reference.strip():
            raise DataContractError("FINRA TAF source reference is required")

    def covers(self, trade_date: date) -> bool:
        return self.effective_from <= trade_date <= self.effective_to


def _select_one(entries: Sequence[object], *, trade_date: date, label: str):
    matching = [entry for entry in entries if entry.covers(trade_date)]  # type: ignore[attr-defined]
    if len(matching) != 1:
        raise PointInTimeError(f"{label} coverage is ambiguous or missing for {trade_date}")
    return matching[0]


def select_section31_rate(entries: Sequence[Section31RateEntry], *, trade_date: date) -> Section31RateEntry:
    return _select_one(entries, trade_date=trade_date, label="Section 31")


def select_finra_taf_rate(entries: Sequence[FinraTafRateEntry], *, trade_date: date) -> FinraTafRateEntry:
    return _select_one(entries, trade_date=trade_date, label="FINRA TAF")


def validate_contiguous_coverage(
    entries: Sequence[Section31RateEntry] | Sequence[FinraTafRateEntry],
    *,
    coverage_start: date,
    coverage_end: date,
    label: str,
) -> None:
    """Require one exact, gap-free, overlap-free interval for every covered date."""

    if coverage_end < coverage_start:
        raise DataContractError("coverage_end precedes coverage_start")
    rows = sorted(entries, key=lambda entry: (entry.effective_from, entry.effective_to))
    if not rows:
        raise DataContractError(f"{label} schedule is empty")
    if rows[0].effective_from != coverage_start:
        raise DataContractError(f"{label} schedule does not begin at coverage_start")
    if rows[-1].effective_to != coverage_end:
        raise DataContractError(f"{label} schedule does not end at coverage_end")
    for left, right in zip(rows, rows[1:]):
        expected = left.effective_to + timedelta(days=1)
        if right.effective_from != expected:
            raise DataContractError(f"{label} schedule has a gap or overlap at {expected}")


def compose_regulatory_fee_schedule(
    section31_entries: Sequence[Section31RateEntry],
    taf_entries: Sequence[FinraTafRateEntry],
    *,
    coverage_start: date,
    coverage_end: date,
) -> tuple[RegulatoryFeeScheduleEntry, ...]:
    """Compose independent official rate histories into non-overlapping fee intervals."""

    validate_contiguous_coverage(
        section31_entries, coverage_start=coverage_start, coverage_end=coverage_end, label="Section 31"
    )
    validate_contiguous_coverage(
        taf_entries, coverage_start=coverage_start, coverage_end=coverage_end, label="FINRA TAF"
    )

    boundaries = {coverage_start, coverage_end + timedelta(days=1)}
    for entry in (*section31_entries, *taf_entries):
        boundaries.add(entry.effective_from)
        if entry.effective_to < coverage_end:
            boundaries.add(entry.effective_to + timedelta(days=1))
    ordered = sorted(boundaries)

    result: list[RegulatoryFeeScheduleEntry] = []
    for start, next_start in zip(ordered, ordered[1:]):
        end = next_start - timedelta(days=1)
        sec = select_section31_rate(section31_entries, trade_date=start)
        taf = select_finra_taf_rate(taf_entries, trade_date=start)
        result.append(
            RegulatoryFeeScheduleEntry(
                effective_from=start,
                effective_to=end,
                sec_section31_per_million=sec.usd_per_million,
                finra_taf_per_share=taf.usd_per_share,
                finra_taf_max_per_trade=taf.maximum_usd_per_trade,
                source_reference=f"{sec.source_reference} + {taf.source_reference}",
            )
        )
    return tuple(result)


def assert_acceptance_period_covered(
    schedule: Sequence[RegulatoryFeeScheduleEntry], *, acceptance_start: date, acceptance_end: date
) -> None:
    if acceptance_end < acceptance_start:
        raise DataContractError("acceptance_end precedes acceptance_start")
    if not schedule:
        raise PointInTimeError("regulatory fee schedule is empty")
    rows = sorted(schedule, key=lambda row: row.effective_from)
    if rows[0].effective_from > acceptance_start:
        raise PointInTimeError("regulatory fee schedule begins after acceptance period")
    last_end = rows[-1].effective_to
    if last_end is None or last_end < acceptance_end:
        raise PointInTimeError("regulatory fee schedule ends before acceptance period")

    cursor = acceptance_start
    while cursor <= acceptance_end:
        matches = [row for row in rows if row.covers(cursor)]
        if len(matches) != 1:
            raise PointInTimeError(f"regulatory fee schedule is ambiguous or missing for {cursor}")
        row = matches[0]
        assert row.effective_to is not None
        cursor = row.effective_to + timedelta(days=1)

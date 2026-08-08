"""Coverage audit primitives for point-in-time SEC filing-header sectors.

This module is provider-agnostic after raw SEC filing-header SIC observations have
been normalized.  It evaluates whether every sector-blind, otherwise-eligible
instrument decision point has a point-in-time sector classification and whether
sector changes remain traceable and non-overlapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Sequence
from uuid import UUID

from .adapters.sec_filing_sic import SecFilingSicObservation, build_sector_history, select_sector_as_of
from .contracts import SectorObservation
from .errors import DataContractError, PointInTimeError
from .time_utils import require_aware


class SectorCoverageError(DataContractError):
    """Raised when the historical-sector coverage contract is violated."""


@dataclass(frozen=True, slots=True)
class SectorCoverageRequirement:
    """One sector-blind decision point that must have a PIT sector value.

    The upstream universe builder must create these rows *without* using sector,
    otherwise the coverage denominator would be circular.
    """

    instrument_id: UUID
    cik: str
    decision_at: datetime
    source_manifest_hash: str
    universe_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_at", require_aware(self.decision_at, "decision_at"))
        cik = self.cik.strip()
        if not cik.isdigit() or int(cik) <= 0:
            raise SectorCoverageError("cik must be a positive numeric identifier")
        object.__setattr__(self, "cik", cik.zfill(10))
        if len(self.source_manifest_hash) != 64:
            raise SectorCoverageError("source_manifest_hash must be a SHA-256 hex digest")
        try:
            int(self.source_manifest_hash, 16)
        except ValueError as exc:
            raise SectorCoverageError("source_manifest_hash must be hexadecimal") from exc
        if not self.universe_version.strip():
            raise SectorCoverageError("universe_version is required")


@dataclass(frozen=True, slots=True)
class SectorCoveragePoint:
    instrument_id: UUID
    cik: str
    decision_at: datetime
    covered: bool
    sector_code: str | None
    sector_label: str | None
    accession_number: str | None
    source_snapshot_id: str | None
    available_at: datetime | None
    missing_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_at", require_aware(self.decision_at, "decision_at"))
        if self.covered:
            if not all((self.sector_code, self.sector_label, self.source_snapshot_id, self.available_at)):
                raise SectorCoverageError("covered point lacks sector lineage")
            if self.missing_reason is not None:
                raise SectorCoverageError("covered point cannot have a missing_reason")
        elif not self.missing_reason:
            raise SectorCoverageError("uncovered point requires a missing_reason")


@dataclass(frozen=True, slots=True)
class SectorChangeReview:
    instrument_id: UUID
    cik: str
    effective_from: datetime
    from_sector: str | None
    to_sector: str
    accession_number: str
    status: str
    reviewer_note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective_from", require_aware(self.effective_from, "effective_from"))
        if self.status not in {"APPROVED", "REJECTED", "PENDING"}:
            raise SectorCoverageError("review status must be APPROVED, REJECTED, or PENDING")
        if not self.to_sector.strip() or not self.accession_number.strip():
            raise SectorCoverageError("sector-change review requires target sector and accession")


@dataclass(frozen=True, slots=True)
class SectorCoverageAudit:
    required_points: int
    covered_points: int
    coverage_ratio: float
    missing_points: tuple[SectorCoveragePoint, ...]
    unresolved_filing_count: int
    sector_change_count: int
    traceable_sector_change_count: int
    interval_overlap_count: int
    approved_manual_reviews: int
    rejected_manual_reviews: int
    representative_header_samples_passed: bool

    @property
    def pass_99_percent_coverage(self) -> bool:
        return self.required_points > 0 and self.coverage_ratio >= 0.99

    @property
    def all_changes_traceable(self) -> bool:
        return self.sector_change_count == self.traceable_sector_change_count

    @property
    def ready_for_gate(self) -> bool:
        return (
            self.pass_99_percent_coverage
            and self.unresolved_filing_count == 0
            and self.all_changes_traceable
            and self.interval_overlap_count == 0
            and self.approved_manual_reviews >= 25
            and self.rejected_manual_reviews == 0
            and self.representative_header_samples_passed
        )


def _validate_interval_history(history: Sequence[SectorObservation]) -> tuple[int, int]:
    overlaps = 0
    traceable_changes = 0
    for index, current in enumerate(history):
        if index == 0:
            continue
        if current.source_snapshot_id.strip():
            traceable_changes += 1
        previous = history[index - 1]
        if previous.effective_to is None or previous.effective_to > current.effective_from:
            overlaps += 1
    return overlaps, traceable_changes


def build_histories_by_instrument(
    observations: Iterable[SecFilingSicObservation],
) -> dict[UUID, tuple[SectorObservation, ...]]:
    grouped: dict[UUID, list[SecFilingSicObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.instrument_id, []).append(observation)
    return {
        instrument_id: build_sector_history(items)
        for instrument_id, items in grouped.items()
    }


def evaluate_sector_coverage(
    requirements: Iterable[SectorCoverageRequirement],
    observations: Iterable[SecFilingSicObservation],
    *,
    unresolved_filing_count: int = 0,
    reviews: Iterable[SectorChangeReview] = (),
    representative_header_samples_passed: bool,
) -> tuple[tuple[SectorCoveragePoint, ...], SectorCoverageAudit]:
    """Evaluate the final P02-G07 coverage contract.

    Coverage is measured only on sector-blind upstream requirements.  A missing
    observation remains missing; the function never backfills a future filing.
    """
    if unresolved_filing_count < 0:
        raise SectorCoverageError("unresolved_filing_count cannot be negative")

    requirement_rows = tuple(requirements)
    if not requirement_rows:
        raise SectorCoverageError("sector coverage requires at least one decision point")
    if len({(row.instrument_id, row.decision_at) for row in requirement_rows}) != len(requirement_rows):
        raise SectorCoverageError("duplicate instrument/decision coverage requirement")

    observation_rows = tuple(observations)
    histories = build_histories_by_instrument(observation_rows) if observation_rows else {}

    accession_by_snapshot: dict[str, str] = {}
    for observation in observation_rows:
        existing = accession_by_snapshot.get(observation.source_snapshot_id)
        if existing is not None and existing != observation.accession_number:
            raise SectorCoverageError("source_snapshot_id maps to multiple SEC accessions")
        accession_by_snapshot[observation.source_snapshot_id] = observation.accession_number

    points: list[SectorCoveragePoint] = []
    for requirement in sorted(requirement_rows, key=lambda item: (str(item.instrument_id), item.decision_at)):
        history = histories.get(requirement.instrument_id, ())
        if not history:
            points.append(
                SectorCoveragePoint(
                    instrument_id=requirement.instrument_id,
                    cik=requirement.cik,
                    decision_at=requirement.decision_at,
                    covered=False,
                    sector_code=None,
                    sector_label=None,
                    accession_number=None,
                    source_snapshot_id=None,
                    available_at=None,
                    missing_reason="NO_FILING_HEADER_SIC_HISTORY",
                )
            )
            continue
        try:
            sector = select_sector_as_of(history, decision_at=requirement.decision_at)
        except PointInTimeError:
            points.append(
                SectorCoveragePoint(
                    instrument_id=requirement.instrument_id,
                    cik=requirement.cik,
                    decision_at=requirement.decision_at,
                    covered=False,
                    sector_code=None,
                    sector_label=None,
                    accession_number=None,
                    source_snapshot_id=None,
                    available_at=None,
                    missing_reason="NO_SECTOR_AVAILABLE_BY_DECISION_TIME",
                )
            )
            continue
        points.append(
            SectorCoveragePoint(
                instrument_id=requirement.instrument_id,
                cik=requirement.cik,
                decision_at=requirement.decision_at,
                covered=True,
                sector_code=sector.sector_code,
                sector_label=sector.sector_label,
                accession_number=accession_by_snapshot.get(sector.source_snapshot_id),
                source_snapshot_id=sector.source_snapshot_id,
                available_at=sector.available_at,
            )
        )

    total = len(points)
    covered = sum(point.covered for point in points)
    missing = tuple(point for point in points if not point.covered)

    interval_overlap_count = 0
    sector_change_count = 0
    traceable_sector_change_count = 0
    actual_change_keys: set[tuple[UUID, datetime, str]] = set()
    for instrument_id, history in histories.items():
        overlaps, traceable = _validate_interval_history(history)
        interval_overlap_count += overlaps
        sector_change_count += max(len(history) - 1, 0)
        traceable_sector_change_count += traceable
        for changed in history[1:]:
            accession = accession_by_snapshot.get(changed.source_snapshot_id)
            if accession:
                actual_change_keys.add((instrument_id, changed.effective_from, accession))

    review_rows = tuple(reviews)
    review_keys = {(row.instrument_id, row.effective_from, row.accession_number) for row in review_rows}
    if len(review_keys) != len(review_rows):
        raise SectorCoverageError("duplicate sector-change review row")
    unknown_reviews = review_keys - actual_change_keys
    if unknown_reviews:
        raise SectorCoverageError("manual review references a non-existent sector change")
    approved = sum(row.status == "APPROVED" for row in review_rows)
    rejected = sum(row.status == "REJECTED" for row in review_rows)

    audit = SectorCoverageAudit(
        required_points=total,
        covered_points=covered,
        coverage_ratio=covered / total,
        missing_points=missing,
        unresolved_filing_count=unresolved_filing_count,
        sector_change_count=sector_change_count,
        traceable_sector_change_count=traceable_sector_change_count,
        interval_overlap_count=interval_overlap_count,
        approved_manual_reviews=approved,
        rejected_manual_reviews=rejected,
        representative_header_samples_passed=representative_header_samples_passed,
    )
    return tuple(points), audit


def summarize_coverage_by_cik(
    requirements: Iterable[SectorCoverageRequirement],
    points: Iterable[SectorCoveragePoint],
) -> tuple[Mapping[str, object], ...]:
    req_by_cik: dict[str, int] = {}
    for requirement in requirements:
        req_by_cik[requirement.cik] = req_by_cik.get(requirement.cik, 0) + 1
    covered_by_cik: dict[str, int] = {}
    for point in points:
        if point.covered:
            covered_by_cik[point.cik] = covered_by_cik.get(point.cik, 0) + 1
    rows = []
    for cik in sorted(req_by_cik):
        required = req_by_cik[cik]
        covered = covered_by_cik.get(cik, 0)
        rows.append(
            {
                "cik": cik,
                "required_points": required,
                "covered_points": covered,
                "coverage_ratio": covered / required,
            }
        )
    return tuple(rows)

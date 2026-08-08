"""Historical SEC filing-header SIC extraction and frozen FF12 sector mapping.

The SEC submissions JSON exposes current top-level SIC metadata. This module instead
uses each filing's immutable complete-submission header, where the filer CIK, assigned
SIC, accession number, and EDGAR acceptance timestamp appear together.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
import re
from typing import Iterable
from uuid import UUID
from zoneinfo import ZoneInfo

from ..contracts import SectorObservation
from ..errors import DataContractError, PointInTimeError
from ..pit import select_latest_known
from ..time_utils import require_aware
from .http import SafeTextClient, TextTransport

UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")

TAXONOMY_ID = "FAMA_FRENCH_12_FROM_SEC_SIC"
TAXONOMY_VERSION = "FF12-SIC-2026-08-05-v1"


class SecFilingHeaderError(DataContractError):
    """Raised when an SEC complete-submission header is missing or ambiguous."""


@dataclass(frozen=True, slots=True)
class SecFilingSicObservation:
    instrument_id: UUID
    cik: str
    accession_number: str
    form_type: str
    sic_code: str
    sic_description: str
    accepted_at: datetime
    available_at: datetime
    source_snapshot_id: str
    revision: int = 0

    def __post_init__(self) -> None:
        accepted = require_aware(self.accepted_at, "accepted_at")
        available = require_aware(self.available_at, "available_at")
        object.__setattr__(self, "accepted_at", accepted)
        object.__setattr__(self, "available_at", available)
        if available < accepted:
            raise SecFilingHeaderError("SIC available_at cannot precede SEC acceptance")
        if not re.fullmatch(r"\d{10}", self.cik):
            raise SecFilingHeaderError("CIK must be zero-padded to ten digits")
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", self.accession_number):
            raise SecFilingHeaderError("invalid SEC accession number")
        if not re.fullmatch(r"\d{4}", self.sic_code) or self.sic_code == "0000":
            raise SecFilingHeaderError("SIC must be a non-zero four-digit code")
        if not self.form_type.strip() or not self.source_snapshot_id.strip():
            raise SecFilingHeaderError("form_type and source_snapshot_id are required")
        if self.revision < 0:
            raise SecFilingHeaderError("revision cannot be negative")


class SecArchivesClient:
    """Read-only client for immutable SEC complete-submission text files."""

    base_url = "https://www.sec.gov"
    adapter_version = "SEC-ARCHIVES-SIC-v0.1.0"

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        transport: TextTransport | None = None,
        requests_per_second: float = 5.0,
    ) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT")
        if not self.user_agent or "@" not in self.user_agent:
            raise ValueError(
                "SEC_USER_AGENT must identify the application and include a monitored contact email"
            )
        if requests_per_second > 10:
            raise ValueError("SEC fair-access limit is at most 10 requests per second")
        self._http = SafeTextClient(
            base_url=self.base_url,
            default_headers={
                "Accept": "text/plain,text/html;q=0.9,*/*;q=0.1",
                "User-Agent": self.user_agent,
            },
            transport=transport,
            requests_per_second=requests_per_second,
        )

    @staticmethod
    def complete_submission_path(cik: str | int, accession_number: str) -> str:
        normalized_cik = _normalize_cik(cik)
        accession = accession_number.strip()
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            raise ValueError("invalid SEC accession number")
        accession_directory = accession.replace("-", "")
        return (
            f"/Archives/edgar/data/{int(normalized_cik)}/"
            f"{accession_directory}/{accession}.txt"
        )

    def complete_submission(self, cik: str | int, accession_number: str) -> str:
        return self._http.get_text(self.complete_submission_path(cik, accession_number))


def _normalize_cik(cik: str | int) -> str:
    try:
        numeric = int(str(cik))
    except ValueError as exc:
        raise ValueError("CIK must be numeric") from exc
    if numeric <= 0:
        raise ValueError("CIK must be positive")
    return f"{numeric:010d}"


def _parse_acceptance(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=NEW_YORK)
    except ValueError as exc:
        raise SecFilingHeaderError(f"invalid SEC acceptance timestamp: {value!r}") from exc
    return parsed.astimezone(UTC)


def _header_only(submission_text: str) -> str:
    if not submission_text.strip():
        raise SecFilingHeaderError("SEC complete-submission text is blank")
    marker = re.search(r"(?im)^\s*<DOCUMENT>\s*$", submission_text)
    return submission_text[: marker.start()] if marker else submission_text


def _single_match(patterns: tuple[str, ...], text: str, field_name: str) -> str:
    values: list[str] = []
    for pattern in patterns:
        values.extend(match.group(1).strip() for match in re.finditer(pattern, text, re.I | re.M))
    distinct = {value for value in values if value}
    if not distinct:
        raise SecFilingHeaderError(f"SEC header lacks {field_name}")
    if len(distinct) > 1:
        raise SecFilingHeaderError(f"SEC header has conflicting {field_name} values")
    return next(iter(distinct))


def _legacy_entity_pairs(header: str) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    for match in re.finditer(r"<COMPANY-DATA>(.*?)</COMPANY-DATA>", header, re.I | re.S):
        block = match.group(1)
        cik_match = re.search(r"<CIK>\s*(\d+)", block, re.I)
        sic_match = re.search(r"<ASSIGNED-SIC>\s*(\d{1,4})", block, re.I)
        if cik_match and sic_match:
            results.append((_normalize_cik(cik_match.group(1)), sic_match.group(1).zfill(4), ""))
    return results


def _text_entity_pairs(header: str) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    starts = [match.start() for match in re.finditer(r"(?im)^\s*COMPANY DATA:\s*$", header)]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(header)
        block = header[start:end]
        cik_match = re.search(r"CENTRAL INDEX KEY:\s*(\d+)", block, re.I)
        sic_line = re.search(r"STANDARD INDUSTRIAL CLASSIFICATION:\s*([^\r\n]+)", block, re.I)
        if not cik_match or not sic_line:
            continue
        raw = sic_line.group(1).strip()
        bracket = re.search(r"\[(\d{1,4})\]", raw)
        fallback = re.search(r"\b(\d{4})\b", raw)
        code_match = bracket or fallback
        if not code_match:
            continue
        description = re.sub(r"\s*\[\d{1,4}\]\s*$", "", raw).strip()
        results.append(
            (_normalize_cik(cik_match.group(1)), code_match.group(1).zfill(4), description)
        )
    return results


def parse_filing_sic(
    submission_text: str,
    *,
    instrument_id: UUID,
    target_cik: str | int,
    source_snapshot_id: str,
    processing_buffer: timedelta = timedelta(minutes=3),
) -> SecFilingSicObservation:
    """Extract the target filer's filing-time SIC from a complete submission.

    The function fails closed when the target CIK is absent or the same filing contains
    conflicting SIC codes for the target entity.
    """
    if processing_buffer < timedelta(0):
        raise ValueError("processing_buffer cannot be negative")
    if not source_snapshot_id.strip():
        raise ValueError("source_snapshot_id is required")

    header = _header_only(submission_text)
    accession = _single_match(
        (
            r"<ACCESSION-NUMBER>\s*([0-9-]+)",
            r"^\s*ACCESSION NUMBER:\s*([0-9-]+)\s*$",
        ),
        header,
        "accession number",
    )
    acceptance_raw = _single_match(
        (
            r"<ACCEPTANCE-DATETIME>\s*(\d{14})",
            r"^\s*ACCEPTANCE-DATETIME:\s*(\d{14})\s*$",
        ),
        header,
        "acceptance timestamp",
    )
    form_type = _single_match(
        (
            r"^\s*<TYPE>\s*([^<\r\n]+)",
            r"^\s*CONFORMED SUBMISSION TYPE:\s*([^\r\n]+)",
        ),
        header,
        "submission type",
    )
    accepted_at = _parse_acceptance(acceptance_raw)
    normalized_target = _normalize_cik(target_cik)

    pairs = _legacy_entity_pairs(header) + _text_entity_pairs(header)
    matching = [(sic, description) for cik, sic, description in pairs if cik == normalized_target]
    if not matching:
        raise SecFilingHeaderError("target CIK has no filing-header SIC")
    distinct_sic = {sic for sic, _ in matching}
    if len(distinct_sic) > 1:
        raise SecFilingHeaderError("target CIK has conflicting SIC codes in one filing")
    sic_code = next(iter(distinct_sic))
    descriptions = {description for sic, description in matching if sic == sic_code and description}
    if len(descriptions) > 1:
        raise SecFilingHeaderError("target CIK has conflicting SIC descriptions in one filing")
    description = next(iter(descriptions), "")

    return SecFilingSicObservation(
        instrument_id=instrument_id,
        cik=normalized_target,
        accession_number=accession,
        form_type=form_type,
        sic_code=sic_code,
        sic_description=description,
        accepted_at=accepted_at,
        available_at=accepted_at + processing_buffer,
        source_snapshot_id=source_snapshot_id,
        revision=1 if form_type.upper().endswith("/A") else 0,
    )


_FF12_LABELS: dict[str, str] = {
    "01_NODUR": "Consumer Nondurables",
    "02_DURBL": "Consumer Durables",
    "03_MANUF": "Manufacturing",
    "04_ENRGY": "Energy",
    "05_CHEMS": "Chemicals",
    "06_BUSEQ": "Business Equipment",
    "07_TELCM": "Telecommunications",
    "08_UTILS": "Utilities",
    "09_SHOPS": "Wholesale, Retail, and Consumer Services",
    "10_HLTH": "Healthcare",
    "11_MONEY": "Finance",
    "12_OTHER": "Other",
}


def _in_any(value: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(lower <= value <= upper for lower, upper in ranges)


def map_sic_to_ff12(sic_code: str | int) -> tuple[str, str]:
    """Map a four-digit SIC code to the frozen Fama-French 12-industry taxonomy."""
    text = str(sic_code).strip()
    if not text.isdigit() or len(text) > 4:
        raise SecFilingHeaderError("SIC must be numeric")
    sic = int(text)
    if sic <= 0 or sic > 9999:
        raise SecFilingHeaderError("SIC is outside the supported range")

    if _in_any(sic, ((100, 999), (2000, 2399), (2700, 2749), (2770, 2799), (3100, 3199), (3940, 3989))):
        code = "01_NODUR"
    elif _in_any(sic, ((2500, 2519), (2590, 2599), (3630, 3659), (3710, 3711), (3714, 3714), (3716, 3716), (3750, 3751), (3792, 3792), (3900, 3939), (3990, 3999))):
        code = "02_DURBL"
    elif _in_any(sic, ((2520, 2589), (2600, 2699), (2750, 2769), (3000, 3099), (3200, 3569), (3580, 3629), (3700, 3709), (3712, 3713), (3715, 3715), (3717, 3749), (3752, 3791), (3793, 3799), (3830, 3839), (3860, 3899))):
        code = "03_MANUF"
    elif _in_any(sic, ((1200, 1399), (2900, 2999))):
        code = "04_ENRGY"
    elif _in_any(sic, ((2800, 2829), (2840, 2899))):
        code = "05_CHEMS"
    elif _in_any(sic, ((3570, 3579), (3660, 3692), (3694, 3699), (3810, 3829), (7370, 7379))):
        code = "06_BUSEQ"
    elif 4800 <= sic <= 4899:
        code = "07_TELCM"
    elif 4900 <= sic <= 4949:
        code = "08_UTILS"
    elif _in_any(sic, ((5000, 5999), (7200, 7299), (7600, 7699))):
        code = "09_SHOPS"
    elif _in_any(sic, ((2830, 2839), (3693, 3693), (3840, 3859), (8000, 8099))):
        code = "10_HLTH"
    elif 6000 <= sic <= 6999:
        code = "11_MONEY"
    else:
        code = "12_OTHER"
    return code, _FF12_LABELS[code]


def build_sector_history(
    observations: Iterable[SecFilingSicObservation],
) -> tuple[SectorObservation, ...]:
    """Create conservative effective intervals from filing-time SIC observations.

    A classification becomes effective only when a filing carrying that SIC is accepted
    and the processing buffer has elapsed. Repeated filings in the same FF12 sector do
    not create redundant intervals. A later changed sector closes the prior interval.
    """
    ordered = sorted(
        observations,
        key=lambda item: (item.available_at, item.revision, item.accession_number),
    )
    if not ordered:
        raise PointInTimeError("sector history requires at least one filing-header SIC")
    instrument_ids = {item.instrument_id for item in ordered}
    ciks = {item.cik for item in ordered}
    if len(instrument_ids) != 1 or len(ciks) != 1:
        raise SecFilingHeaderError("sector history cannot mix instruments or CIKs")

    unique_accessions: dict[str, SecFilingSicObservation] = {}
    for item in ordered:
        existing = unique_accessions.get(item.accession_number)
        if existing is not None and existing != item:
            raise SecFilingHeaderError("conflicting SIC observations share an accession number")
        unique_accessions[item.accession_number] = item
    ordered = sorted(
        unique_accessions.values(),
        key=lambda item: (item.available_at, item.revision, item.accession_number),
    )

    changes: list[tuple[SecFilingSicObservation, str, str]] = []
    previous_code: str | None = None
    for item in ordered:
        sector_code, sector_label = map_sic_to_ff12(item.sic_code)
        if sector_code != previous_code:
            changes.append((item, sector_code, sector_label))
            previous_code = sector_code

    intervals: list[SectorObservation] = []
    for index, (item, sector_code, sector_label) in enumerate(changes):
        effective_to = changes[index + 1][0].available_at if index + 1 < len(changes) else None
        intervals.append(
            SectorObservation(
                instrument_id=item.instrument_id,
                taxonomy_id=TAXONOMY_ID,
                taxonomy_version=TAXONOMY_VERSION,
                sector_code=sector_code,
                sector_label=sector_label,
                effective_from=item.available_at,
                effective_to=effective_to,
                available_at=item.available_at,
                source_snapshot_id=item.source_snapshot_id,
                revision=item.revision,
            )
        )
    return tuple(intervals)


def select_sector_as_of(
    observations: Iterable[SectorObservation],
    *,
    decision_at: datetime,
) -> SectorObservation:
    decision = require_aware(decision_at, "decision_at")
    eligible = [
        item
        for item in observations
        if item.effective_from <= decision
        and (item.effective_to is None or decision < item.effective_to)
        and item.available_at <= decision
    ]
    return select_latest_known(eligible, decision_at=decision)

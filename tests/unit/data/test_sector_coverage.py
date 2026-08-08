from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from trading_bot.data.adapters.sec_filing_sic import parse_filing_sic
from trading_bot.data.sector_coverage import (
    SectorChangeReview,
    SectorCoverageError,
    SectorCoverageRequirement,
    evaluate_sector_coverage,
)

UTC = timezone.utc
HASH = "a" * 64


def filing(accession: str, acceptance: str, sic: str, description: str = "TEST") -> str:
    return f"""<SEC-DOCUMENT>{accession}.txt : 20250201
<SEC-HEADER>{accession}.hdr.sgml : 20250201
<ACCEPTANCE-DATETIME>{acceptance}
ACCESSION NUMBER:               {accession}
CONFORMED SUBMISSION TYPE:      10-Q
FILER:
    COMPANY DATA:
        COMPANY CONFORMED NAME:          TEST COMPANY
        CENTRAL INDEX KEY:               0000320193
        STANDARD INDUSTRIAL CLASSIFICATION: {description} [{sic}]
<DOCUMENT>
"""


def req(instrument_id, decision_at):
    return SectorCoverageRequirement(
        instrument_id=instrument_id,
        cik="320193",
        decision_at=decision_at,
        source_manifest_hash=HASH,
        universe_version="sector-blind-v1",
    )


def test_future_sector_change_does_not_backfill_earlier_requirement():
    instrument_id = uuid4()
    first = parse_filing_sic(
        filing("0000320193-25-000001", "20250201161530", "3571", "ELECTRONIC COMPUTERS"),
        instrument_id=instrument_id,
        target_cik="320193",
        source_snapshot_id="snap-1",
    )
    later = parse_filing_sic(
        filing("0000320193-25-000002", "20250801162000", "5734", "RETAIL STORES"),
        instrument_id=instrument_id,
        target_cik="320193",
        source_snapshot_id="snap-2",
    )
    requirements = (
        req(instrument_id, datetime(2025, 1, 31, 21, 30, tzinfo=UTC)),
        req(instrument_id, datetime(2025, 6, 30, 20, 30, tzinfo=UTC)),
        req(instrument_id, datetime(2025, 9, 30, 20, 30, tzinfo=UTC)),
    )
    points, audit = evaluate_sector_coverage(
        requirements,
        [first, later],
        unresolved_filing_count=0,
        reviews=(),
        representative_header_samples_passed=True,
    )
    assert points[0].covered is False
    assert points[0].missing_reason == "NO_SECTOR_AVAILABLE_BY_DECISION_TIME"
    assert points[1].sector_code == "06_BUSEQ"
    assert points[2].sector_code == "09_SHOPS"
    assert audit.coverage_ratio == pytest.approx(2 / 3)
    assert audit.sector_change_count == 1
    assert audit.traceable_sector_change_count == 1
    assert audit.ready_for_gate is False


def test_gate_requires_99_percent_zero_unresolved_and_25_approved_real_changes():
    instrument_id = uuid4()
    observations = []
    base = datetime(2018, 1, 2, 15, 0, tzinfo=UTC)
    for index in range(26):
        accepted = base + timedelta(days=90 * index)
        local = accepted.astimezone(timezone(timedelta(hours=-5)))
        stamp = local.strftime("%Y%m%d%H%M%S")
        accession = f"0000320193-{18 + index // 4:02d}-{index + 1:06d}"
        sic = "3571" if index % 2 == 0 else "5734"
        observations.append(
            parse_filing_sic(
                filing(accession, stamp, sic),
                instrument_id=instrument_id,
                target_cik="320193",
                source_snapshot_id=f"snap-{index}",
            )
        )

    requirements = tuple(
        req(instrument_id, observations[-1].available_at + timedelta(days=30 * i + 1))
        for i in range(100)
    )
    reviews = tuple(
        SectorChangeReview(
            instrument_id=instrument_id,
            cik="0000320193",
            effective_from=observations[index].available_at,
            from_sector="06_BUSEQ" if index % 2 else "09_SHOPS",
            to_sector="09_SHOPS" if index % 2 else "06_BUSEQ",
            accession_number=observations[index].accession_number,
            status="APPROVED",
        )
        for index in range(1, 26)
    )
    _, audit = evaluate_sector_coverage(
        requirements,
        observations,
        unresolved_filing_count=0,
        reviews=reviews,
        representative_header_samples_passed=True,
    )
    assert audit.coverage_ratio == 1.0
    assert audit.sector_change_count == 25
    assert audit.approved_manual_reviews == 25
    assert audit.ready_for_gate is True

    _, blocked = evaluate_sector_coverage(
        requirements,
        observations,
        unresolved_filing_count=1,
        reviews=reviews,
        representative_header_samples_passed=True,
    )
    assert blocked.ready_for_gate is False


def test_duplicate_requirement_fails_closed():
    instrument_id = uuid4()
    requirement = req(instrument_id, datetime(2025, 3, 31, 20, 30, tzinfo=UTC))
    with pytest.raises(SectorCoverageError):
        evaluate_sector_coverage(
            [requirement, requirement],
            [],
            representative_header_samples_passed=True,
        )

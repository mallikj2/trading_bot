from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from trading_bot.data.adapters.sec_sector_crawl import (
    CrawlCheckpoint,
    SecSectorCoverageCrawler,
)
from trading_bot.data.adapters.storage import RawSnapshotStore
from trading_bot.data.sector_coverage import SectorCoverageRequirement, evaluate_sector_coverage

UTC = timezone.utc


def master(day: date, accession: str) -> str:
    return f"""Description: Master Index
CIK|Company Name|Form Type|Date Filed|Filename
--------------------------------------------------------------------------------
320193|TEST CO|10-Q|{day.isoformat()}|edgar/data/320193/{accession}.txt
"""


def filing(accession: str, acceptance: str, sic: str, description: str) -> str:
    return f"""<SEC-DOCUMENT>{accession}.txt
<SEC-HEADER>{accession}.hdr.sgml
<ACCEPTANCE-DATETIME>{acceptance}
ACCESSION NUMBER:               {accession}
CONFORMED SUBMISSION TYPE:      10-Q
FILER:
    COMPANY DATA:
        COMPANY CONFORMED NAME:          TEST CO
        CENTRAL INDEX KEY:               0000320193
        STANDARD INDUSTRIAL CLASSIFICATION: {description} [{sic}]
<DOCUMENT>
"""


class FakeDailyIndexClient:
    adapter_version = "fake-index"

    def __init__(self):
        self.days = {
            date(2025, 1, 31): "0000320193-25-000001",
            date(2025, 7, 31): "0000320193-25-000002",
        }

    def quarter_directory(self, year: int, quarter: int):
        items = []
        for day in self.days:
            q = ((day.month - 1) // 3) + 1
            if day.year == year and q == quarter:
                items.append({"name": f"master.{day:%Y%m%d}.idx"})
        return {"directory": {"item": items}}

    def master_index(self, filing_date: date):
        return master(filing_date, self.days[filing_date])


class FakeArchiveClient:
    adapter_version = "fake-archive"

    def __init__(self):
        self.payloads = {
            "0000320193-25-000001": filing(
                "0000320193-25-000001", "20250131161530", "3571", "ELECTRONIC COMPUTERS"
            ),
            "0000320193-25-000002": filing(
                "0000320193-25-000002", "20250731162000", "5734", "RETAIL STORES"
            ),
        }

    def complete_submission(self, cik, accession_number):
        return self.payloads[accession_number]


def test_offline_crawl_builds_point_in_time_history_and_reuses_checkpoint(tmp_path: Path):
    instrument_id = uuid4()
    requirements = (
        SectorCoverageRequirement(
            instrument_id=instrument_id,
            cik="320193",
            decision_at=datetime(2025, 6, 30, 20, 30, tzinfo=UTC),
            source_manifest_hash="a" * 64,
            universe_version="sector-blind-v1",
        ),
        SectorCoverageRequirement(
            instrument_id=instrument_id,
            cik="320193",
            decision_at=datetime(2025, 8, 29, 20, 30, tzinfo=UTC),
            source_manifest_hash="a" * 64,
            universe_version="sector-blind-v1",
        ),
    )
    crawler = SecSectorCoverageCrawler(
        daily_index_client=FakeDailyIndexClient(),
        archives_client=FakeArchiveClient(),
        snapshot_store=RawSnapshotStore(tmp_path / "raw"),
        checkpoint=CrawlCheckpoint(tmp_path / "checkpoint.json"),
    )
    results = crawler.crawl(requirements)
    assert len(results) == 1
    assert results[0].selected_filing_count == 2
    assert results[0].parsed_filing_count == 2
    assert results[0].failures == ()

    points, audit = evaluate_sector_coverage(
        requirements,
        results[0].observations,
        unresolved_filing_count=0,
        reviews=(),
        representative_header_samples_passed=True,
    )
    assert [point.sector_code for point in points] == ["06_BUSEQ", "09_SHOPS"]
    assert audit.coverage_ratio == 1.0

    # Re-running uses the persisted complete-submission payloads from the checkpoint.
    second = crawler.crawl(requirements)
    assert second[0].parsed_filing_count == 2

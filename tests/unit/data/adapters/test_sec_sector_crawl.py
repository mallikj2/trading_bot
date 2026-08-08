from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

import pytest

from trading_bot.data.adapters.sec_sector_crawl import (
    CrawlCheckpoint,
    SecSectorCrawlError,
    blocked_result,
    master_index_names,
    parse_master_index,
    parse_target_ledger,
)

UTC = timezone.utc

MASTER = """Description:           Master Index of EDGAR Dissemination Feed
Last Data Received:    March 31, 2025
Comments:              webmaster@sec.gov

CIK|Company Name|Form Type|Date Filed|Filename
--------------------------------------------------------------------------------
320193|APPLE INC|10-Q|2025-01-31|edgar/data/320193/0000320193-25-000001.txt
1652044|ALPHABET INC|10-K|2025-02-05|edgar/data/1652044/0001652044-25-000002.txt
"""


def test_parse_master_index_and_accession_identity():
    rows = parse_master_index(MASTER)
    assert rows[0].cik == "0000320193"
    assert rows[0].accession_number == "0000320193-25-000001"
    assert rows[0].filing_date == date(2025, 1, 31)


def test_master_index_conflict_fails_closed():
    conflict = MASTER + "320193|DIFFERENT|8-K|2025-01-31|edgar/data/320193/0000320193-25-000001.txt\n"
    with pytest.raises(SecSectorCrawlError):
        parse_master_index(conflict)


def test_directory_parser_keeps_only_master_indexes():
    payload = {
        "directory": {
            "item": [
                {"name": "master.20250102.idx"},
                {"name": "form.20250102.idx"},
                {"name": "master.20250103.idx"},
            ]
        }
    }
    assert master_index_names(payload) == ("master.20250102.idx", "master.20250103.idx")


def test_target_ledger_must_be_sector_blind():
    instrument_id = uuid4()
    payload = {
        "sector_blind": True,
        "rows": [
            {
                "instrument_id": str(instrument_id),
                "cik": "320193",
                "decision_at": "2025-01-31T21:30:00+00:00",
                "source_manifest_hash": "b" * 64,
                "universe_version": "u1",
            }
        ],
    }
    rows = parse_target_ledger(payload)
    assert rows[0].cik == "0000320193"
    bad = dict(payload)
    bad["sector_blind"] = False
    with pytest.raises(SecSectorCrawlError):
        parse_target_ledger(bad)


def test_checkpoint_is_atomic_and_resumable(tmp_path: Path):
    checkpoint = CrawlCheckpoint(tmp_path / "state.json")
    checkpoint.put("320193", "0000320193-25-000001", {"status": "SUCCESS", "snapshot_id": "s1"})
    reloaded = CrawlCheckpoint(tmp_path / "state.json")
    assert reloaded.get("0000320193", "0000320193-25-000001")["snapshot_id"] == "s1"


def test_blocked_result_makes_no_coverage_claims():
    result = blocked_result(reasons=["SEC_USER_AGENT_WITH_MONITORED_CONTACT_REQUIRED"])
    assert result["status"] == "BLOCKED"
    assert result["claims"]["full_sec_crawl_completed"] is False

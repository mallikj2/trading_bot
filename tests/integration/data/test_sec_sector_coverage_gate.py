from pathlib import Path

import json
import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_p02_g07_remains_blocked_until_real_crawl_and_sector_blind_denominator_exist():
    cfg = yaml.safe_load((ROOT / "configs/data/phase02_data_gate_audit.yaml").read_text())
    gate = next(row for row in cfg["mandatory_gates"] if row["id"] == "P02-G07")
    assert gate["status"] == "BLOCKED"
    assert "SECTOR_BLIND_PIT_TARGET_LEDGER_REQUIRED" in gate["reason"]
    assert cfg["integration_result"]["pass"] == 11
    assert cfg["integration_result"]["blocked"] == 7

    result = json.loads((ROOT / "SEC_SECTOR_COVERAGE_RESULTS.json").read_text())
    assert result["gate_id"] == "P02-G07"
    assert result["status"] == "BLOCKED"
    assert result["claims"]["full_sec_crawl_completed"] is False

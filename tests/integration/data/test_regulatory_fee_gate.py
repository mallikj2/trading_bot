from datetime import date
from pathlib import Path

import yaml

from trading_bot.data.regulatory_fees import (
    FinraTafRateEntry,
    Section31RateEntry,
    assert_acceptance_period_covered,
    compose_regulatory_fee_schedule,
)

ROOT = Path(__file__).resolve().parents[3]


def test_p02_g17_is_pass_and_frozen_schedule_is_contiguous() -> None:
    gate_cfg = yaml.safe_load((ROOT / "configs/data/phase02_data_gate_audit.yaml").read_text())
    gate = next(row for row in gate_cfg["mandatory_gates"] if row["id"] == "P02-G17")
    assert gate["status"] == "PASS"
    assert gate["evidence"] == "docs/phases/PHASE_02_REGULATORY_FEE_BASIS_FREEZE.md"
    assert gate_cfg["integration_result"]["conditional"] == 0

    cfg = yaml.safe_load((ROOT / "configs/data/regulatory_fee_basis.yaml").read_text())
    start = date.fromisoformat(cfg["coverage"]["effective_from"])
    end = date.fromisoformat(cfg["coverage"]["effective_to"])
    sec = tuple(
        Section31RateEntry(
            effective_from=date.fromisoformat(row["from"]),
            effective_to=date.fromisoformat(row["to"]),
            usd_per_million=row["rate"],
            source_reference=row["source"],
        )
        for row in cfg["section31_usd_per_million"]
    )
    taf = tuple(
        FinraTafRateEntry(
            effective_from=date.fromisoformat(row["from"]),
            effective_to=date.fromisoformat(row["to"]),
            usd_per_share=row["per_share"],
            maximum_usd_per_trade=row["cap_per_trade"],
            source_reference=row["source"],
        )
        for row in cfg["finra_taf_equity"]
    )
    schedule = compose_regulatory_fee_schedule(sec, taf, coverage_start=start, coverage_end=end)
    assert_acceptance_period_covered(schedule, acceptance_start=date(2016, 1, 1), acceptance_end=end)

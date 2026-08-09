from __future__ import annotations

from pathlib import Path

import pytest

from trading_bot.platform.pre_purchase_gate import run_pre_purchase_gate


@pytest.fixture(scope="module")
def gate_result(tmp_path_factory):
    repo_root = Path(__file__).resolve().parents[3]
    work = tmp_path_factory.mktemp("pf_gate")
    return run_pre_purchase_gate(repo_root, work_dir=work).to_dict()


def test_integrated_pre_purchase_gate_passes(gate_result) -> None:
    assert gate_result["gate_id"] == "P02-PF-GATE"
    assert gate_result["status"] == "PASS"
    assert gate_result["summary"] == {"total": 10, "pass": 10, "fail": 0}


def test_integrated_gate_does_not_authorize_spend_or_phase03(gate_result) -> None:
    assert gate_result["procurement_ready_for_manual_approval"] is True
    assert gate_result["procurement_authorized"] is False
    assert gate_result["phase03_authorized"] is False
    assert gate_result["strategy_profitability_validated"] is False


def test_integrated_gate_covers_mandatory_cross_subsystem_evidence(gate_result) -> None:
    checks = {row["check_id"]: row for row in gate_result["checks"]}
    assert set(checks) == {
        "ALL_PF_TASKS_PASS",
        "STRATEGY_VALIDATION_CONTROLS",
        "LEADS_AND_WATCHLIST",
        "SIMULATION_OMS_JOURNAL_REPLAY",
        "RUNTIME_STATE_ENFORCEMENT",
        "RECOVERY_RECONCILIATION",
        "ALERT_INCIDENT_INTEGRATION",
        "EXPERIMENT_LINEAGE",
        "READ_ONLY_UI_AND_ZERO_LIVE_MUTATION",
        "NO_EMBEDDED_COMMERCIAL_CREDENTIALS",
    }
    assert all(row["status"] == "PASS" for row in checks.values())
    assert checks["RECOVERY_RECONCILIATION"]["evidence"]["broker_submission_count"] == 1
    assert checks["READ_ONLY_UI_AND_ZERO_LIVE_MUTATION"]["evidence"]["methods"] == ["GET"]
    assert checks["NO_EMBEDDED_COMMERCIAL_CREDENTIALS"]["evidence"]["findings"] == []


def test_integrated_gate_evidence_is_non_profitability_synthetic(gate_result) -> None:
    assert gate_result["evidence_class"] == "SYNTHETIC_PRE_PURCHASE_GATE"
    experiment = next(row for row in gate_result["checks"] if row["check_id"] == "EXPERIMENT_LINEAGE")
    assert experiment["evidence"]["registry"]["status"] == "PASS"

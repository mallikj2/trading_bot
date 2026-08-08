import json
from pathlib import Path

from trading_bot.data.adapters import corporate_action_trial


def _clear(monkeypatch):
    for key in (
        "EDI_CORPORATE_ACTIONS_EXPORT_PATH",
        "EDI_CORPORATE_ACTIONS_LICENSE_APPROVED",
        "DATABENTO_API_KEY",
        "DATABENTO_CORPORATE_ACTIONS_LICENSE_APPROVED",
    ):
        monkeypatch.delenv(key, raising=False)


def test_environment_status_is_fail_closed(monkeypatch):
    _clear(monkeypatch)
    status = corporate_action_trial.environment_status()
    assert status["edi_export_present"] is False
    assert status["edi_license_approved"] is False
    assert status["databento_api_key"] == "MISSING"


def test_edi_export_trial_requires_explicit_license(monkeypatch, tmp_path):
    _clear(monkeypatch)
    export = tmp_path / "edi.json"
    export.write_text("[]", encoding="utf-8")
    result = corporate_action_trial.run_edi_export_trial(golden_cases=[{"case_id": "x"}], export_path=export)
    assert result["status"] == "BLOCKED"


def test_runner_writes_blocked_evidence_without_credentials(monkeypatch, tmp_path):
    _clear(monkeypatch)
    golden = tmp_path / "golden.json"
    golden.write_text(json.dumps({"cases": [{
        "case_id": "NVDA_2024_FORWARD_SPLIT",
        "symbol": "NVDA",
        "action_type": "SPLIT",
        "effective_date": "2024-06-10",
        "split_old_shares": "1",
        "split_new_shares": "10"
    }]}), encoding="utf-8")
    output = tmp_path / "result.json"
    result = corporate_action_trial.run_trial(golden_path=golden, output=output)
    assert result["status"] == "BLOCKED"
    assert result["gate"] == "P02-G09"
    assert output.is_file()

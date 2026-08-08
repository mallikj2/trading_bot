from datetime import date

from trading_bot.data.adapters.pit_companion_trial import environment_status, run_smoke


def _clear(monkeypatch):
    for name in (
        "DATABENTO_API_KEY",
        "DATABENTO_RESEARCH_LICENSE_APPROVED",
        "DATABENTO_EXECUTION_DATASET",
        "DATABENTO_US_EQUITIES_DATASET",
        "DATABENTO_EXECUTION_COVERAGE_APPROVED",
    ):
        monkeypatch.delenv(name, raising=False)


def test_trial_blocks_without_credential_and_governance_evidence(monkeypatch):
    _clear(monkeypatch)
    result = run_smoke(ticker="AAPL", as_of_date=date(2025, 12, 31))
    assert result["status"] == "BLOCKED"
    assert result["checks"][0]["status"] == "BLOCKED"


def test_execution_coverage_is_a_separate_approval_gate(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("DATABENTO_API_KEY", "secret")
    monkeypatch.setenv("DATABENTO_RESEARCH_LICENSE_APPROVED", "true")
    monkeypatch.setenv("DATABENTO_EXECUTION_DATASET", "EQUS.MINI")
    assert environment_status()["trial_ready"] is False
    monkeypatch.setenv("DATABENTO_EXECUTION_COVERAGE_APPROVED", "true")
    assert environment_status()["trial_ready"] is True

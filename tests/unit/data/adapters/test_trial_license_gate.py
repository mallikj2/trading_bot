from __future__ import annotations

from trading_bot.data.adapters.trial import environment_status


def test_massive_key_without_research_license_does_not_make_trial_ready(monkeypatch) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", "secret")
    monkeypatch.setenv("SEC_USER_AGENT", "QuantBot research@example.com")
    monkeypatch.delenv("MASSIVE_RESEARCH_LICENSE_APPROVED", raising=False)

    status = environment_status()

    assert status["massive_credentials"] == "AVAILABLE"
    assert status["massive_research_license"] == "NOT_APPROVED"
    assert status["credentialed_trial_ready"] is False


def test_massive_trial_requires_explicit_license_approval(monkeypatch) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", "secret")
    monkeypatch.setenv("MASSIVE_RESEARCH_LICENSE_APPROVED", "true")
    monkeypatch.setenv("SEC_USER_AGENT", "QuantBot research@example.com")

    status = environment_status()

    assert status["massive_research_license"] == "APPROVED"
    assert status["credentialed_trial_ready"] is True

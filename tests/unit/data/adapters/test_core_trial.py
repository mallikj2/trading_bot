from trading_bot.data.adapters import core_trial


def _clear(monkeypatch):
    for key in (
        "KIBOT_USERNAME",
        "KIBOT_PASSWORD",
        "KIBOT_PRIVATE_RESEARCH_LICENSE_APPROVED",
        "DATABENTO_API_KEY",
        "DATABENTO_RESEARCH_LICENSE_APPROVED",
        "DATABENTO_US_EQUITIES_DATASET",
        "SEC_USER_AGENT",
    ):
        monkeypatch.delenv(key, raising=False)


def test_core_trial_environment_is_fail_closed(monkeypatch):
    _clear(monkeypatch)
    status = core_trial.environment_status()
    assert status["selected_core_price_provider"] == "KIBOT"
    assert status["core_price_trial_ready"] is False
    assert status["databento_companion_trial_ready"] is False
    assert status["full_market_data_stack_trial_ready"] is False


def test_core_price_ready_requires_credentials_and_license_ack(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("KIBOT_USERNAME", "user")
    monkeypatch.setenv("KIBOT_PASSWORD", "pw")
    monkeypatch.setenv("KIBOT_PRIVATE_RESEARCH_LICENSE_APPROVED", "true")
    status = core_trial.environment_status()
    assert status["core_price_trial_ready"] is True
    assert status["full_market_data_stack_trial_ready"] is False


def test_databento_companion_requires_credentials_license_and_dataset(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("DATABENTO_API_KEY", "db-test")
    monkeypatch.setenv("DATABENTO_RESEARCH_LICENSE_APPROVED", "true")
    status = core_trial.environment_status()
    assert status["databento_companion_trial_ready"] is False
    monkeypatch.setenv("DATABENTO_US_EQUITIES_DATASET", "TEST.US.EQUITIES")
    status = core_trial.environment_status()
    assert status["databento_companion_trial_ready"] is True

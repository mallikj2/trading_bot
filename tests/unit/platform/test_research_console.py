from datetime import datetime, timezone

from trading_bot.platform.research_console import build_fixture_console


def test_fixture_console_has_expected_lead_and_watchlist_projection():
    console = build_fixture_console(as_of=datetime(2026, 8, 8, 20, 30, tzinfo=timezone.utc))
    leads = console.trade_leads()
    watchlist = console.watchlist()
    assert {row["symbol"] for row in leads} == {"ALFA", "GAMM", "DELT"}
    assert {row["symbol"] for row in watchlist} == {"BETA", "GAMM", "DELT"}
    assert all(row["content_hash"] for row in leads)


def test_overview_is_research_only_and_phase03_locked():
    overview = build_fixture_console().overview()
    assert overview["runtime_state"] == "RESEARCH_ONLY"
    assert overview["phase03_authorized"] is False
    assert overview["procurement_authorized"] is False
    assert "No live orders" in overview["fixture_notice"]


def test_portfolio_and_risk_are_explicitly_synthetic_and_non_trading():
    console = build_fixture_console()
    portfolio = console.portfolio()
    risk = console.risk()
    assert portfolio["mode"] == "SYNTHETIC_RESEARCH_PLACEHOLDER"
    assert risk["new_risk_allowed"] is False
    assert "NO_LIVE_ORDER_SUBMISSION" in risk["hard_boundaries"]


def test_watchlist_explains_future_qualification_condition():
    entries = build_fixture_console().watchlist()
    beta = next(row for row in entries if row["symbol"] == "BETA")
    assert beta["blocking_reasons"][0]["code"] == "SCORE_THRESHOLD_NOT_MET"
    assert any("future decision cycle" in action for action in beta["qualification_actions"])

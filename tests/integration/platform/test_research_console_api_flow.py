from fastapi.testclient import TestClient

from trading_bot.platform.api.research_api import create_app
from trading_bot.platform.research_console import build_fixture_console


def test_tradelead_to_api_watchlist_and_audit_flow_is_consistent():
    with TestClient(create_app(build_fixture_console())) as client:
        leads = client.get("/api/v1/leads").json()
        watchlist = client.get("/api/v1/watchlist").json()
        audit = client.get("/api/v1/audit").json()
        lead_ids = {row["lead_id"] for row in leads}
        watch_ids = {row["lead_id"] for row in watchlist}
        audit_ids = {row["entity_id"] for row in audit}
        assert lead_ids <= audit_ids
        assert watch_ids <= audit_ids
        assert {row["symbol"] for row in watchlist} == {"BETA", "GAMM", "DELT"}


def test_governance_and_health_are_visible_without_secrets():
    with TestClient(create_app(build_fixture_console())) as client:
        gates = client.get("/api/v1/gates").json()
        health = client.get("/api/v1/data-health").json()
        combined = str(gates) + str(health)
        assert "P02-PF01" in combined
        assert "P02-G18" in combined
        for secret_word in ("PASSWORD", "API_KEY", "TOKEN", "SECRET"):
            assert secret_word not in combined.upper()

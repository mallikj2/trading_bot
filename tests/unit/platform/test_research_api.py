from fastapi.testclient import TestClient

from trading_bot.platform.api.research_api import READ_ONLY_METHODS, create_app
from trading_bot.platform.research_console import build_fixture_console


def test_all_openapi_operations_are_read_only():
    app = create_app(build_fixture_console())
    schema = app.openapi()
    methods = {
        method.upper()
        for operations in schema["paths"].values()
        for method in operations
        if not method.startswith("x-")
    }
    assert methods <= READ_ONLY_METHODS
    assert not ({"POST", "PUT", "PATCH", "DELETE"} & methods)


def test_expected_read_routes_respond():
    app = create_app(build_fixture_console())
    with TestClient(app) as client:
        for path in (
            "/api/v1/health",
            "/api/v1/overview",
            "/api/v1/leads",
            "/api/v1/watchlist",
            "/api/v1/portfolio",
            "/api/v1/risk",
            "/api/v1/gates",
            "/api/v1/data-health",
            "/api/v1/audit",
            "/api/v1/strategy-validation",
        ):
            response = client.get(path)
            assert response.status_code == 200, path


def test_mutation_paths_do_not_exist():
    app = create_app(build_fixture_console())
    with TestClient(app) as client:
        for method in (client.post, client.put, client.patch, client.delete):
            response = method("/api/v1/leads")
            assert response.status_code == 405
        for path in ("/api/v1/orders", "/api/v1/buy", "/api/v1/sell", "/api/v1/cancel"):
            assert client.get(path).status_code == 404


def test_openapi_description_declares_research_only_contract():
    schema = create_app(build_fixture_console()).openapi()
    assert "Read-only" in schema["info"]["description"]
    assert "broker/order mutation" in schema["info"]["description"]

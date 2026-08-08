from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web" / "src"


def test_frontend_api_client_uses_get_only():
    source = (WEB / "lib" / "api.ts").read_text()
    assert "method: 'GET'" in source
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert f"method: '{method}'" not in source


def test_frontend_has_no_secret_storage_or_broker_urls():
    all_source = "\n".join(path.read_text() for path in WEB.rglob("*") if path.is_file())
    forbidden = ("localStorage", "sessionStorage", "Authorization:", "api_key", "schwab.com", "developer.schwab")
    for token in forbidden:
        assert token not in all_source


def test_frontend_exposes_required_pf02_views():
    app = (WEB / "App.tsx").read_text()
    for label in ("Overview", "Trade Leads", "Watchlist", "Portfolio", "Risk", "Phase Gates", "Data Health", "Audit Trail"):
        assert label in app


def test_frontend_contains_no_order_mutation_endpoint():
    all_source = "\n".join(path.read_text().lower() for path in WEB.rglob("*") if path.is_file())
    for path in ("/orders", "/buy", "/sell", "/cancel"):
        assert path not in all_source

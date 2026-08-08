"""FastAPI read-only surface for the Phase 02B Research Console."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trading_bot.platform.research_console import ReadOnlyResearchConsole, build_fixture_console

READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


def create_app(console: ReadOnlyResearchConsole | None = None) -> FastAPI:
    service = console or build_fixture_console()
    app = FastAPI(
        title="Quant Trading Bot Research Console API",
        version="0.2-pf02",
        description=(
            "Read-only Phase 02 research/operations API. No broker/order mutation routes "
            "exist in this application."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.get("/api/v1/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "READ_ONLY_RESEARCH"}

    @app.get("/api/v1/overview", tags=["research"])
    def overview():
        return service.overview()

    @app.get("/api/v1/leads", tags=["research"])
    def leads():
        return service.trade_leads()

    @app.get("/api/v1/watchlist", tags=["research"])
    def watchlist():
        return service.watchlist()

    @app.get("/api/v1/portfolio", tags=["research"])
    def portfolio():
        return service.portfolio()

    @app.get("/api/v1/risk", tags=["research"])
    def risk():
        return service.risk()

    @app.get("/api/v1/gates", tags=["governance"])
    def gates():
        return service.gates()

    @app.get("/api/v1/data-health", tags=["governance"])
    def data_health():
        return service.data_health()

    @app.get("/api/v1/audit", tags=["governance"])
    def audit():
        return service.audit()

    schema = app.openapi()
    forbidden = []
    for path, operations in schema.get("paths", {}).items():
        for method in operations:
            upper = method.upper()
            if upper not in READ_ONLY_METHODS and not method.startswith("x-"):
                forbidden.append(f"{upper} {path}")
    if forbidden:
        raise RuntimeError(f"PF02 read-only contract violated: {forbidden}")

    return app


app = create_app()

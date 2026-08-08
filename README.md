# Phase 02B — P02-PF02 Read-Only Research Console Bundle

This is the cumulative repository-ready Phase 02 bundle after completing the second task in the reshaped pre-purchase platform foundation.

## Result

```text
P02-PF01 TRADELEAD_AND_WATCHLIST_DOMAIN = PASS
P02-PF02 READ_ONLY_API_AND_RESEARCH_CONSOLE = PASS
P02-PF03 EVENT_JOURNAL_AND_DETERMINISTIC_REPLAY = NEXT
```

PF02 adds a GET-only FastAPI API and a React + TypeScript Research Console for Overview, Trade Leads, Watchlist, synthetic Portfolio, Risk boundaries, Phase Gates, Data Health, and Audit Trail.

It does **not** add broker connectivity, provider credentials, paper/live trading, mutation routes, browser secret storage, or frontend strategy logic.

## Current governance state

```text
PHASE_02=ACTIVE_RESHAPED
P02-PF-GATE=BLOCKED_REMAINING_TASKS
PROCUREMENT_AUTHORIZED=false
PROCUREMENT_READY_FOR_MANUAL_APPROVAL=false
PHASE03_AUTHORIZED=false
```

## New primary files

- `src/trading_bot/platform/research_console.py`
- `src/trading_bot/platform/api/research_api.py`
- `web/src/App.tsx`
- `web/src/pages/`
- `web/src/lib/`
- `docs/platform/READ_ONLY_RESEARCH_CONSOLE_CONTRACT.md`
- `docs/phases/PHASE_02_PF02_READ_ONLY_RESEARCH_CONSOLE.md`
- `configs/platform/research_console.yaml`
- `OPENAPI_PF02.json`
- `PF02_RESEARCH_CONSOLE_RESULTS.json`
- `tests/unit/platform/test_research_api.py`
- `tests/integration/platform/test_research_console_api_flow.py`

## Validation

- **330 Python tests passed + 12 taxonomy subtests**
- **5 Node/TypeScript frontend view-model tests passed**
- React/TypeScript source type validation passed
- live Uvicorn/OpenAPI smoke test passed
- OpenAPI: 9 routes, GET only
- YAML/JSON validation passed
- no frontend broker/secret/mutation path detected

The sandbox's internal npm mirror does not expose the public React/Vite packages, so the Vite production bundle was not built here. The React source and view-model logic were still type/test validated, and the package is configured for normal public npm installation.

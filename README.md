# Phase 02B — P02-PF04 Runtime Safety State + Protections Bundle

This is the cumulative repository-ready Phase 02 bundle after completing the fourth task in the reshaped pre-purchase platform foundation.

## Result

```text
P02-PF01 TRADELEAD_AND_WATCHLIST_DOMAIN = PASS
P02-PF02 READ_ONLY_API_AND_RESEARCH_CONSOLE = PASS
P02-PF03 EVENT_JOURNAL_AND_DETERMINISTIC_REPLAY = PASS
P02-PF04 RUNTIME_SAFETY_STATE_AND_PROTECTIONS = PASS
P02-PF05 LOOKAHEAD_AND_RECURSIVE_VALIDATION = NEXT
```

PF04 adds deterministic `ACTIVE / REDUCING / HALTED` runtime safety states, point-in-time protection evidence, automatic escalation, explicit-only recovery, journal/replay integration, and read-only Risk Console visibility.

It does **not** change strategy alpha, authorize broker mutations, connect commercial credentials, deploy paper/live trading, authorize procurement, or authorize Phase 03.

## Current governance state

```text
PHASE_02=ACTIVE_RESHAPED
P02-PF-GATE=BLOCKED_REMAINING_TASKS
PROCUREMENT_AUTHORIZED=false
PROCUREMENT_READY_FOR_MANUAL_APPROVAL=false
PHASE03_AUTHORIZED=false
```

## New primary files

- `src/trading_bot/platform/runtime_safety.py`
- `configs/platform/runtime_safety.yaml`
- `docs/platform/RUNTIME_SAFETY_PROTECTIONS_CONTRACT.md`
- `docs/phases/PHASE_02_PF04_RUNTIME_SAFETY_PROTECTIONS.md`
- `PF04_RUNTIME_SAFETY_RESULTS.json`
- `tests/unit/platform/test_runtime_safety.py`
- `tests/integration/platform/test_runtime_safety_event_flow.py`
- `OPENAPI_PF04.json`

PF02 files were also updated so the read-only Risk screen exposes PF04 state/protections without gaining any mutation routes.

## Validation

- **371 Python tests passed + 12 taxonomy subtests**
- **19 focused PF04 safety tests passed**
- **5 Node/TypeScript frontend view-model tests passed**
- TypeScript application validation passed
- Python compilation passed
- FastAPI OpenAPI smoke validation passed: **9 GET-only routes, 0 mutation routes**
- YAML/JSON validation passed
- deterministic safety journal/replay passed
- SHA-256 package verification passed

The existing PF02 sandbox limitation remains: a Vite production bundle cannot be built here because the sandbox does not have the public React/Vite dependency set installed. TypeScript source validation and view-model tests pass; no PF04 frontend dependency was added.


## Phase 02B PF05

P02-PF05 adds deterministic lookahead and recursive strategy validation. Clean synthetic CSMOM-LS-v0.2 fixtures pass, while deliberately future-dependent ranking/exit logic and arbitrary-history-start dependence fail as required. The Research Console now exposes a read-only Strategy Validation view.

See `README_PF05_STRATEGY_VALIDATION.md`.

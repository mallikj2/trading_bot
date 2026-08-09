# Validation Results — P02-PF08 Experiment Registry + Reporting + Attribution

**Result:** PASS  
**Date:** 2026-08-08

## Cumulative automated validation

- Python test suite: **437 passed**
- Taxonomy subtests: **12 passed**
- PF08-focused experiment/API/integration tests: **22 passed** in focused validation
- Frontend Node/TypeScript view-model tests: **5 passed**
- TypeScript application validation: **PASS**
- Python compilation: **PASS**
- OpenAPI paths: **11**
- OpenAPI mutation methods: **0**
- YAML parse validation: **PASS**
- JSON parse validation: **PASS**
- PF08 fixture CLI/registry verification: **3 definitions / 3 runs / PASS**
- Synthetic evidence labels: **NOT_STRATEGY_EVIDENCE**
- `strategy_profitability_validated`: **false**
- `phase03_acceptance_backtest`: **false**

## Experiment-registry acceptance

Validated:

- deterministic definition IDs;
- deterministic run IDs and independent result hashes;
- required strategy/code/data/universe/parameter/cost provenance;
- append-only SQLite registry;
- identical duplicate registration is idempotent;
- update/delete attempts rejected;
- offline tampering detected;
- registry close/reopen preserves run/result identities;
- attribution identity reconciles net = long + short + costs;
- positive cost components rejected;
- PF08 rejects `PHASE03_ACCEPTANCE` evidence;
- baseline-relative comparison is deterministic and does not select a winner.

## Research Console

`GET /api/v1/experiments` exposes synthetic PF08 experiment/reporting fixtures. The UI includes an Experiments & Attribution page. All API operations remain GET-only.

## Frontend build environment limitation

`npm run build` could not complete in this sandbox because the `vite` executable is not installed in the available npm environment (`vite: not found`). TypeScript validation and view-model tests pass. No production Vite-build claim is made.

## Governance

```text
P02-PF08 = PASS
P02-PF09 = NEXT
P02-PF-GATE = BLOCKED_REMAINING_TASKS
PROCUREMENT_AUTHORIZED = false
PROCUREMENT_READY_FOR_MANUAL_APPROVAL = false
PHASE03_AUTHORIZED = false
```

No strategy profitability, deployed paper-trading, live trading, paid-provider, or broker result is claimed.

# Validation Results — P02-PF-GATE Integrated Pre-Purchase Platform Foundation

**Date:** 2026-08-08  
**Gate:** `P02-PF-GATE`  
**Outcome:** **PASS**

## Integrated gate

`PYTHONPATH=src python -m trading_bot.platform.pre_purchase_gate_cli . --output P02_PF_GATE_RESULTS.json`

Result: **10/10 integrated checks PASS**.

The checks cover:

- PF01–PF10 individual PASS state;
- PF05 clean lookahead/recursive controls and contaminated-control failures;
- deterministic TradeLead/Watchlist identity and blocker reasons;
- OMS/fills, journal completeness, reopen/replay determinism;
- `REDUCING` runtime enforcement;
- crash-window recovery without duplicate broker submit;
- Recovery → Alert/Incident journal integration;
- immutable `SIMULATION_ONLY` experiment lineage;
- GET-only Research Console API and network-free SimulatedBroker;
- embedded commercial credential scan.

## Cumulative Python regression

```text
477 passed, 12 subtests passed in 26.57s
```

Command:

```bash
PYTHONPATH=src pytest -q
```

The dedicated integrated gate test file contributes **4 tests**, all passing.

## Frontend validation

```text
5 Node/TypeScript view-model tests PASS
TypeScript type validation PASS
```

Commands:

```bash
cd web
npm run test:view-models
npm run validate:types
```

The Research Console OpenAPI has **13 paths** and exactly one operation method class: **GET**. There are no POST/PUT/PATCH/DELETE routes.

### Production-build environment limitation

`npm run build` completes the TypeScript step and then fails because this sandbox does not provide the `vite` executable:

```text
sh: 1: vite: not found
```

Therefore the final Vite production-bundle step is **not claimed as passed**. This is an environment/dependency-installation limitation, not substituted with fabricated evidence.

## Structural validation

- Python compile/compileall: PASS
- YAML parse: **27 files PASS**
- JSON parse: **39 files PASS**
- OpenAPI generation: PASS
- Gate CLI: PASS
- Known secret-file/token scan: PASS, no findings
- No commercial provider credentials used
- No Schwab/live broker connection used

## Governance result

```text
P02-PF01..P02-PF10 = PASS
P02-PF-GATE = PASS
PROCUREMENT_READY_FOR_MANUAL_APPROVAL = true
PROCUREMENT_AUTHORIZED = false
PHASE03_AUTHORIZED = false
STRATEGY_PROFITABILITY_VALIDATED = false
```

The existing 18 Phase 02 data gates remain unchanged at **11 PASS / 7 BLOCKED / 0 CONDITIONAL**.

# Phase 02 — Core Research Provider Selection and Trial Package

This is the cumulative repository-ready Phase 02 bundle through the core provider license-selection and credentialed representative-trial preparation task.

## Current status

- Kibot private/personal retained EOD archive license decision: **PASS (scope-bound)**
- Kibot paid representative trial: **BLOCKED — credentials not present**
- PIT security-master/exact-execution companion: **BLOCKED — Databento or equivalent not yet licensed/trialed**
- Cumulative automated tests: **219 passed + 12 taxonomy subtests**
- Phase 02 final gate: **NOT READY**
- Phase 03 final acceptance backtest: **NOT AUTHORIZED**

Mandatory Phase 02 audit: **10 PASS / 7 BLOCKED / 1 CONDITIONAL** across **18** gates.

## New or changed files in this task

- `src/trading_bot/data/adapters/kibot.py`
- `src/trading_bot/data/adapters/databento_companion.py`
- `src/trading_bot/data/adapters/core_trial.py`
- `src/trading_bot/data/adapters/storage.py`
- `tests/unit/data/adapters/test_kibot_adapter.py`
- `tests/unit/data/adapters/test_databento_companion.py`
- `tests/unit/data/adapters/test_core_trial.py`
- `configs/data/core_provider_stack.yaml`
- `configs/data/phase02_data_gate_audit.yaml`
- `docs/phases/PHASE_02_CORE_PROVIDER_SELECTION_AND_TRIAL.md`
- `docs/data/CORE_PROVIDER_LICENSE_DECISION.md`
- `docs/data/CORE_PROVIDER_REPRESENTATIVE_TRIAL_RUNBOOK.md`
- `docs/data/CORE_PROVIDER_EVIDENCE_REGISTER.md`
- `docs/data/PHASE_02_DATA_GATE_INTEGRATION_AUDIT.md`
- `docs/project/CURRENT_STATE_PHASE_02_CORE_PROVIDER_PATCH.md`
- `docs/project/DECISIONS_PHASE_02_CORE_PROVIDER_APPEND.md`
- `CORE_PROVIDER_ENVIRONMENT_STATUS.json`
- `CORE_PROVIDER_TRIAL_RESULTS.json`
- `PHASE02_GATE_AUDIT_RESULTS.json`

## Binding provider-stack decisions

- Kibot is the first paid **retained unadjusted EOD archive** candidate.
- Kibot back-adjusted files are never canonical raw history.
- Kibot ticker is never a stable security identifier.
- Kibot is prohibited as the sole point-in-time security master because ticker renames rewrite history and ticker reuse can concatenate unrelated issuers.
- Databento is the preferred companion trial candidate for PIT security-master records and exact historical trades; its project license/account gate remains blocked.
- Final Phase 01 10:00–10:30 ET acceptance VWAP must use validated trades/equivalent exact records, never OHLC approximation.
- A historical vendor archive does not prove same-day close+30m data availability; that timing contract requires separate evidence.

## Remaining Phase 02 blockers

1. paid Kibot representative-case trial;
2. PIT security-master/exact-execution companion license and trial;
3. full SEC historical-sector coverage crawl;
4. provider reconciliation for complex corporate actions;
5. revision-aware historical earnings source sample/license;
6. observed-spread quote source and calibration panel;
7. historical securities-lending source/license/coverage;
8. full acceptance-period regulatory-fee basis remains conditional.

Do not start the Phase 03 final acceptance backtest until every mandatory gate in `configs/data/phase02_data_gate_audit.yaml` is `PASS`.

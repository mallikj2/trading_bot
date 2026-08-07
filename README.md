# Phase 02 — Financing / Cash Carry + Final Data-Gate Integration Audit

This is the cumulative repository-ready Phase 02 bundle through the financing/cash-carry engineering task and integration audit.

## Current status

- Financing/cash-carry engineering: **PASS**
- Cumulative automated tests: **205 passed + 12 taxonomy subtests**
- Phase 02 final gate: **NOT READY**
- Phase 03 final acceptance backtest: **NOT AUTHORIZED**

Mandatory Phase 02 audit: **9 PASS / 7 BLOCKED / 1 CONDITIONAL**.

## New files in this task

- `src/trading_bot/data/financing.py`
- `src/trading_bot/data/gates.py`
- `tests/unit/data/test_financing.py`
- `tests/unit/data/test_phase02_gates.py`
- `tests/integration/data/test_financing_strategy_bridge.py`
- `tests/integration/data/test_phase02_gate_snapshot.py`
- `configs/data/financing_cash_carry.yaml`
- `configs/data/phase02_data_gate_audit.yaml`
- `docs/phases/PHASE_02_FINANCING_AND_DATA_GATE_AUDIT.md`
- `docs/data/FINANCING_CASH_CARRY_CONTRACT.md`
- `docs/data/FINANCING_SOURCE_EVALUATION.md`
- `docs/data/FINANCING_EVIDENCE_REGISTER.md`
- `docs/data/PHASE_02_DATA_GATE_INTEGRATION_AUDIT.md`
- `docs/project/CURRENT_STATE_PHASE_02_FINANCING_GATE_AUDIT_PATCH.md`
- `docs/project/DECISIONS_PHASE_02_FINANCING_GATE_AUDIT_APPEND.md`
- `PHASE02_GATE_AUDIT_RESULTS.json`

## Binding financing rules

- Primary cash earns zero.
- Short-sale proceeds are restricted collateral.
- Short proceeds cannot fund the long sleeve.
- Gross leverage above 1.0 fails closed.
- Any positive settled debit fails closed under the current mandate.
- FRED DTB3 is optional cash-opportunity attribution only, not broker income.
- Phase 01 pessimistic stress doubles financing costs, not positive carry.

## Remaining Phase 02 blockers

1. approved core research provider non-display/retention license;
2. credentialed representative-case provider trial;
3. full historical-sector coverage crawl;
4. provider reconciliation for complex corporate actions;
5. revision-aware historical earnings source sample/license;
6. observed-spread quote source and calibration panel;
7. historical securities-lending source/license/coverage;
8. full acceptance-period regulatory-fee basis is still conditional.

Do not start the Phase 03 final acceptance backtest until the machine-readable gate register contains only PASS statuses for all mandatory gates.

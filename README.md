# Phase 02 Cumulative Repository Bundle — Through Historical Short-Borrow Modeling

This cumulative bundle contains the approved Phase 01 reference strategy plus all Phase 02 implementation work completed through the historical short-borrow availability and borrow-cost modeling task.

Latest task status:

- **Engineering:** PASS
- **Historical borrow source:** BLOCKED pending approved research/retention license and credentialed coverage evidence
- **Live Schwab shorting:** PROHIBITED pending account/broker borrow validation
- **Phase 02 overall:** ACTIVE

New primary files:

- `docs/phases/PHASE_02_HISTORICAL_SHORT_BORROW.md`
- `docs/data/HISTORICAL_SHORT_BORROW_CONTRACT.md`
- `docs/data/SHORT_BORROW_SOURCE_EVALUATION.md`
- `docs/data/SHORT_BORROW_PROVIDER_TRIAL_RUNBOOK.md`
- `docs/data/SHORT_BORROW_EVIDENCE_REGISTER.md`
- `configs/data/historical_short_borrow.yaml`
- `src/trading_bot/data/borrow.py`
- `src/trading_bot/data/adapters/ortex_borrow.py`
- `tests/unit/data/test_borrow.py`
- `tests/unit/data/adapters/test_ortex_borrow.py`
- `tests/integration/data/test_short_borrow_strategy_bridge.py`
- `tests/fixtures/data/borrow_history_cases.json`
- `docs/project/CURRENT_STATE_PHASE_02_BORROW_PATCH.md`
- `docs/project/DECISIONS_PHASE_02_BORROW_APPEND.md`

The implementation does not claim licensed securities-lending coverage, historical strategy profitability, paper-trading readiness, or live-short authorization.

## Material source-governance result

S&P Global Securities Finance is the preferred technical historical-borrow candidate, with DataLend/EquiLend as the secondary institutional candidate. ORTEX is technically useful and has a retail API, but its standard consumer retention terms conflict with this project's immutable raw-snapshot/reproducibility policy. ORTEX research ingestion is therefore gated behind explicit separate license approval.

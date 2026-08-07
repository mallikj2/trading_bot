# Phase 02 Cumulative Repository Bundle — Through Spread Calibration / Transaction Costs

This cumulative bundle contains the approved Phase 01 reference strategy plus all Phase 02 implementation work completed through the historical spread-calibration and transaction-cost input task.

Latest task status:

- **Engineering:** PASS
- **Historical observed-quote calibration:** BLOCKED pending licensed source
- **Phase 02 overall:** ACTIVE

New primary files:

- `docs/phases/PHASE_02_HISTORICAL_SPREAD_AND_TRANSACTION_COSTS.md`
- `docs/data/HISTORICAL_SPREAD_CALIBRATION_CONTRACT.md`
- `docs/data/TRANSACTION_COST_INPUT_CONTRACT.md`
- `docs/data/SPREAD_QUOTE_SOURCE_EVALUATION.md`
- `docs/data/SPREAD_CALIBRATION_CREDENTIALED_RUNBOOK.md`
- `docs/data/TRANSACTION_FEE_EVIDENCE_REGISTER.md`
- `configs/data/historical_spread_transaction_cost.yaml`
- `src/trading_bot/data/costs.py`
- `tests/unit/data/test_spread_costs.py`
- `tests/unit/data/adapters/test_massive_quotes.py`
- `tests/integration/data/test_spread_cost_pipeline.py`
- `docs/project/CURRENT_STATE_PHASE_02_SPREAD_COST_PATCH.md`
- `docs/project/DECISIONS_PHASE_02_SPREAD_COST_APPEND.md`

The bundle does not claim provider-license approval, paid quote-data calibration, strategy profitability, paper-trading readiness, or live-trading readiness.


## Material provider-license correction

The previously proposed Massive one-month Advanced historical quote download-and-retain workflow has been withdrawn. Massive's public Individual Market Data Terms are not sufficient for this project's non-display strategy-research and post-termination retention requirements. See `docs/data/PROVIDER_LICENSE_GOVERNANCE_CORRECTION.md`.

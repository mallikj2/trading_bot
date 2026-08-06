# Phase 02 Complex Corporate-Action and Total-Return Bundle

This is a cumulative repository overlay for the Quant Trading Bot project. It contains the Phase 02 kernel, production adapters, historical-sector implementation, and the new complex corporate-action/point-in-time total-return implementation.

## Merge destination

Copy the bundle contents into the repository root.

Important new or changed paths:

```text
src/trading_bot/data/total_returns.py
src/trading_bot/data/strategy_inputs.py
src/trading_bot/data/contracts.py
src/trading_bot/data/hashing.py
src/trading_bot/strategies/csmom_ls_v0_2.py
tests/unit/data/test_total_returns.py
tests/integration/data/test_total_return_strategy_pipeline.py
tests/unit/strategies/test_csmom_ls_v0_2.py
configs/data/corporate_action_total_return.yaml
docs/data/CORPORATE_ACTION_TOTAL_RETURN_CONTRACT.md
docs/data/POINT_IN_TIME_TOTAL_RETURN_ALGORITHM.md
docs/phases/PHASE_02_COMPLEX_CORPORATE_ACTION_TOTAL_RETURN.md
```

## Validate

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m compileall -q src tests
```

Expected test result for this bundle:

```text
119 passed, 12 subtests passed
```

## Status

- Complex corporate-action implementation: PASS.
- Provider completeness and retention evidence: CONDITIONAL / OPEN.
- Phase 02 overall: ACTIVE.
- Phase 03 final acceptance backtest, paper trading, and live trading: not authorized.

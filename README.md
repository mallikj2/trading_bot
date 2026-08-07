# Phase 02 Revision-Aware Historical Earnings Bundle

This is a cumulative repository overlay for the Quant Trading Bot project. It contains the Phase 02 kernel, provider adapters, historical-sector implementation, complex corporate-action/total-return engine, and the revision-aware historical earnings schedule implementation.

## Important new paths

```text
src/trading_bot/data/earnings.py
tests/unit/data/test_earnings_schedule.py
tests/integration/data/test_earnings_strategy_bridge.py
tests/fixtures/data/earnings_revision_cases.json
configs/data/revision_aware_earnings.yaml
docs/data/EARNINGS_SCHEDULE_POINT_IN_TIME_CONTRACT.md
docs/data/EARNINGS_SOURCE_EVALUATION.md
docs/data/EARNINGS_PROVIDER_TRIAL_RUNBOOK.md
docs/data/EARNINGS_PROVIDER_EVIDENCE_REGISTER.md
docs/phases/PHASE_02_REVISION_AWARE_EARNINGS_SCHEDULE.md
docs/project/CURRENT_STATE_PHASE_02_EARNINGS_PATCH.md
docs/project/DECISIONS_PHASE_02_EARNINGS_APPEND.md
```

## Validate

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m compileall -q src tests
```

Observed validation for this package build: `143 passed, 12 subtests passed`; focused earnings suite: `24 passed`. See `VALIDATION_RESULTS.md` for details.

## Status

- Revision-aware earnings implementation: PASS.
- Historical source evidence: CONDITIONAL / OPEN.
- Preferred source: Wall Street Horizon DateBreaks + Earnings Date Daily Snapshots, pending credentialed sample and license.
- Phase 02 overall: ACTIVE.
- Phase 03 final acceptance backtest, paper trading, and live trading: not authorized.

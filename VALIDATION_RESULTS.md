# Validation Results — Phase 02 Historical Spread Calibration and Transaction-Cost Inputs

**Date:** 2026-08-06  
**Task status:** `IMPLEMENTATION_PASS_CALIBRATION_SOURCE_BLOCKED`  
**Phase 02 overall:** `ACTIVE`

## Automated validation

- `PYTHONPATH=src pytest -q` -> **165 passed, 12 subtests passed**.
- `python -m compileall -q src tests` -> **PASS**.
- All **8 YAML** configuration files parsed successfully.
- All **3 JSON** artifacts/fixtures parsed successfully.
- Credentialed provider trial entrypoint -> **BLOCKED as designed** because project credentials are unavailable and the Massive research license flag is not approved.

## Focused spread / cost coverage

Validated behaviors include:

- Corwin-Schultz proxy uses only completed daily bars available by decision time.
- Future execution-window NBBO targets cannot enter earlier calibration fits.
- Time-weighted 10:00–10:30 ET NBBO spread requires a valid prevailing start quote and full 1,800-second state coverage.
- Crossed and non-positive quote states fail closed.
- Liquidity calibration uses the frozen Phase 01 ADV60 buckets.
- Missing calibration buckets fail closed.
- Phase 01 spread boundary is exact: `<= 35 bps` passes and `> 35 bps` blocks.
- Benchmark VWAP, half-spread, residual slippage, market impact, broker commission, SEC Section 31, and FINRA TAF are separately attributed.
- Buy trades do not receive sell-side regulatory assessments.
- Regulatory fee schedule gaps/overlaps fail closed.
- Pessimistic scenario doubles the modeled cost components as required by Phase 01.
- Phase 03 slippage/impact coefficients have no hidden production defaults.

## Provider-license hardening

A material source-governance correction was incorporated before packaging:

- Massive's public Individual Market Data Terms were reviewed and are not treated as authorization for this project's non-display strategy research or post-termination data retention.
- The previously proposed one-month Massive Advanced `download -> retain -> cancel/downgrade` workflow is withdrawn unless separate written rights are obtained.
- The provider trial now requires both a Massive credential and explicit `MASSIVE_RESEARCH_LICENSE_APPROVED=true` authorization.
- Two unit tests verify that a credential alone cannot make the research trial ready.
- Databento historical and Cboe DataShop are recorded as **evaluation candidates only**, not approved providers.

## Live/credentialed evidence not claimed

No historical observed-quote panel was downloaded in this task. No quote calibration accuracy, provider completeness, provider license approval, or paid-data retention right is claimed.

The spread blocker remains open until a provider/dataset passes:

1. use-rights review;
2. cost and coverage approval;
3. credentialed deterministic quote-panel acquisition;
4. minimum 500 known calibration points per ADV60 bucket;
5. calibration error/coverage report;
6. frozen model artifact with immutable lineage.

## Current external fee evidence encoded for contract tests

- Schwab current online listed-stock/ETF commission: USD 0.
- SEC Section 31: USD 20.60 per USD 1,000,000 of covered sales effective 2026-04-04.
- FINRA 2026 covered-equity TAF: USD 0.000195/share, capped at USD 9.79/trade.

These are effective-dated evidence examples. They are not silently backfilled into historical periods.

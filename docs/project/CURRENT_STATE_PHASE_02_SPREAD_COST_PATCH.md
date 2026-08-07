# CURRENT_STATE — Phase 02 Spread / Cost Patch

**Date:** 2026-08-06

## Phase status

`PHASE_02_DATA_AND_POINT_IN_TIME_DESIGN = ACTIVE`

## Newly completed engineering work

- Historical NBBO quote contract implemented.
- Massive historical quote adapter implemented; adapter version `MASSIVE-STOCKS-v0.2.1`.
- Time-weighted 10:00-10:30 ET observed spread target implemented.
- Corwin-Schultz point-in-time spread proxy implemented.
- Walk-forward liquidity-bucket spread calibrator implemented.
- Frozen 35 bps Phase 01 spread gate implemented and boundary-tested.
- Effective-dated regulatory-fee contract implemented.
- Decomposed transaction-cost input model implemented.
- Pessimistic 2x cost multiplier supported.
- Exact residual slippage and market-impact parameters remain deferred to Phase 03 as previously approved.

## B02-05 status

`HISTORICAL_SPREAD_QUOTE_MODEL = IMPLEMENTATION_PASS_CALIBRATION_SOURCE_BLOCKED`

Still required:

1. historical quote provider/dataset selected with explicit non-display research and retention rights;
2. quote-data acquisition cost and coverage approval;
3. credentialed deterministic calibration panel;
4. >=500 valid observations in each ADV60 bucket;
5. frozen calibration model and coverage/error report.

## Data-budget and license status

- recurring mandate ceiling: USD 80/month;
- Massive public Individual Market Data Terms are **not approved** for this project's non-display strategy research/retention use;
- the earlier one-month Massive Advanced retain-then-downgrade proposal is withdrawn unless separate written terms are obtained;
- Databento historical usage-based data is the next evaluation candidate, pending exact coverage/cost/account-license review;
- Cboe DataShop historical equity NBBO products are a secondary candidate, pending price/license review;
- no quote provider is currently approved.

## Remaining Phase 02 blockers/open gates

- credentialed representative-case provider trial;
- core provider license approval;
- full historical-sector coverage crawl;
- earnings historical sample and retention-license approval;
- complex corporate-action provider reconciliation;
- historical spread credentialed calibration run;
- historical short-borrow availability and cost model;
- any remaining full-period regulatory-fee schedule required by the later Phase 03 fee-basis decision.

Phase 03 final acceptance testing remains prohibited.

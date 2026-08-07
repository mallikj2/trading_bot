# DECISIONS — Phase 02 Spread / Cost Append

**Date:** 2026-08-06

## D02-SPREAD-01 — Observed future quotes are calibration targets, not prior-close filters

**Decision:** The next-session NBBO stream may calibrate and validate the historical spread model but may not directly determine whether the prior-close signal passes the 35 bps gate.

**Reason:** Direct use would introduce look-ahead bias.

## D02-SPREAD-02 — Use Corwin-Schultz as the first-stage historical spread proxy

**Decision:** Use the two-day high-low Corwin-Schultz estimator from completed daily bars as the low-frequency pre-trade proxy.

**Constraint:** Raw proxy values must not be represented as observed spread. Production use requires historical quote calibration.

## D02-SPREAD-03 — Freeze robust liquidity-bucket calibration architecture

**Decision:** Calibrate by the four Phase 01 ADV60 buckets with historical-only median ratios and median observed spreads. Acceptance configuration requires at least 500 known observations per bucket.

**Reason:** Simple, auditable, low-parameter calibration reduces overfit risk.

## D02-SPREAD-04 — Preserve the exact 35 bps boundary

**Decision:** `<= 35 bps` passes the spread dimension; `> 35 bps` blocks new positions.

## D02-SPREAD-05 — Massive public individual terms do not authorize this research path

**Decision:** The earlier proposal to use Massive Advanced temporarily for quote calibration and retain the downloaded data after cancellation/downgrade is withdrawn. Under Massive's public Individual Market Data Terms reviewed on 2026-08-06, the project must not use Massive market data for this non-display strategy-research workflow unless a separate written license explicitly permits the intended use and retention.

**Effect:** Massive adapters remain testable code but are governance-disabled for research. A credential alone is insufficient; `MASSIVE_RESEARCH_LICENSE_APPROVED=true` is also required by the trial entrypoint.

## D02-SPREAD-06 — Historical quote provider selection remains open

**Decision:** Evaluate Databento historical usage-based data first and Cboe DataShop historical equity NBBO products second. Neither is approved until exact coverage, cost, credentials, and applicable use/retention terms pass the trial.

## D02-COST-01 — Separate benchmark, price adversity, cash fees and borrow economics

**Decision:** Transaction costs are decomposed into:

- Phase 01 VWAP benchmark;
- half modeled spread;
- residual slippage;
- market impact;
- commission;
- regulatory fees;
- separate borrow/financing/distribution modules.

No opaque all-purpose slippage field is permitted.

## D02-COST-02 — Do not freeze Phase 03 slippage/impact parameters in Phase 02

**Decision:** Exact residual-slippage, impact and fee-basis choices remain Phase 03 responsibilities under the approved reconciliation.

**Exception:** The Phase 01 pessimistic multiplier of 2x remains frozen and implemented.

## D02-COST-03 — Regulatory fees are effective-dated and fail closed

**Decision:** Missing or overlapping fee-schedule coverage invalidates the cost calculation when that fee-basis mode is used.

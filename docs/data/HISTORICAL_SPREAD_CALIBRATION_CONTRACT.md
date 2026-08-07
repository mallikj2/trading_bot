# Historical Spread Calibration Contract

**Strategy:** `CSMOM-LS-v0.2`  
**Status:** Implementation complete; observed-quote calibration conditional  
**Date:** 2026-08-06

## 1. Binding Phase 01 requirement

The approved strategy blocks a new position when the **final modeled spread exceeds 35 basis points**. The threshold is inclusive: 35.0000 bps is eligible; any larger value is not.

The spread gate is a **pre-trade decision input**. Therefore it must be computable from information available at the strategy decision timestamp. The next-session 10:00-10:30 ET quote stream is future information and may not be used directly to decide whether the prior-close signal was tradable.

## 2. Two-layer design

### 2.1 Pre-trade proxy

The first-stage estimator is the Corwin-Schultz two-day high-low estimator computed from the two most recent completed, valid daily bars.

For days `t-1` and `t`:

- `beta = log(H[t-1]/L[t-1])^2 + log(H[t]/L[t])^2`
- `gamma = log(max(H[t-1], H[t]) / min(L[t-1], L[t]))^2`
- the standard Corwin-Schultz alpha and spread transform are applied;
- negative alpha is floored at zero;
- the result is expressed in basis points.

Both bars must satisfy `available_at <= decision_at`. A current/future revision is prohibited.

The estimator is intentionally treated as a **proxy**, not as observed historical spread. Corwin and Schultz developed it from daily high/low prices as a low-frequency bid-ask estimator; the project calibrates it before use rather than assuming its raw level is execution-realistic.

## 3. Observed calibration target

The calibration target is the **time-weighted NBBO quoted spread** during the exact Phase 01 execution benchmark window:

`10:00:00 inclusive to 10:30:00 exclusive America/New_York`

For each prevailing NBBO state:

`spread_bps = 10,000 * (ask - bid) / ((ask + bid) / 2)`

The target is weighted by the number of seconds for which each NBBO state prevailed.

Requirements:

1. a complete positive bid and ask;
2. `ask >= bid`;
3. one prevailing state at window start;
4. the window-start quote must be no older than 60 seconds;
5. sequence/timestamp ambiguity fails closed;
6. raw quote snapshots and hashes are retained subject to provider licensing.

Locked markets (`ask == bid`) may contribute zero spread. Crossed markets are rejected.

## 4. Point-in-time calibration

A calibration point contains:

- prior-close daily spread proxy;
- Phase 01 `ADV60` known at that decision;
- later execution-window observed NBBO spread;
- target quote availability timestamp;
- complete source lineage.

A model fit at time `T` may use only calibration points whose proxy and observed target both satisfy:

`available_at <= T`

The calibrator must never use a future target and then backfill the fitted multiplier into earlier decisions.

## 5. Liquidity stratification

Calibration is separated into the frozen eligible-universe liquidity buckets:

1. USD 25M <= ADV60 < USD 50M
2. USD 50M <= ADV60 < USD 100M
3. USD 100M <= ADV60 < USD 250M
4. ADV60 >= USD 250M

The production acceptance configuration requires at least **500 known calibration observations per bucket**.

## 6. Robust calibration function

For each historical calibration point:

`x = max(raw_corwin_schultz_bps, 1 bp)`

`ratio = observed_nbbo_spread_bps / x`

Within each liquidity bucket the model stores:

- median ratio;
- median observed spread;
- observation count.

The pre-trade predicted spread is:

`predicted = max(bucket_median_observed, x * bucket_median_ratio)`

and is capped at 100 bps for data-quality containment. The Phase 01 trade gate then applies the separate 35 bps maximum.

This calibration is intentionally simple and robust. No coefficient search or strategy-P&L optimization is permitted in Phase 02.

## 7. Deterministic calibration sampling

Full-market quote retention is unnecessary for this strategy. The credentialed trial should create a deterministic, stratified calibration panel:

- only securities in the point-in-time eligible universe;
- 10 names per ADV60 bucket per weekly entry date where available;
- selection by lowest SHA-256 of `(instrument_id | decision_session_date | calibration_version)`;
- at least two years of quote-calibration warm-up before the untouched acceptance interval;
- identical selection rules across all years.

This avoids cherry-picking and substantially reduces quote volume.

## 8. Provider and license boundary

The calibration engine is provider-independent. Historical observed quotes may be loaded only from a source whose rights are approved for this exact use.

### Massive governance correction

Massive's public Individual Market Data Terms reviewed on 2026-08-06 make the previously proposed one-month Advanced acquisition unsuitable without a separate written agreement. The public terms state, among other restrictions, that market data is display-only absent another agreement, non-display / investment-strategy derivative use requires licensing, and market data must be deleted on account termination.

Therefore the earlier `download -> retain -> downgrade/cancel` proposal is **withdrawn**. Massive may be reconsidered only if separate written terms expressly permit this project's non-display research and retention needs.

### Current source shortlist

1. **Databento historical** — preferred next evaluation because historical data is usage-based and the public licensing guidance states T+1 historical data generally does not require an exchange license. Exact US-equity quote coverage, total request cost and post-download rights still require account-specific verification.
2. **Cboe DataShop Equity & ETF Quotes / Trades** — documented 2010-present historical equity coverage with bid/ask or NBBO fields and one-time historical purchasing. Exact price and rights for the deterministic sample must be confirmed.
3. **Other licensed historical quote sources** — acceptable if they meet the same point-in-time, cost and retention contract.

The recurring USD 80/month mandate ceiling remains binding. A one-time or usage-based historical acquisition may be considered only with explicit spend approval and approved rights; it does not silently amend the recurring budget.

## 9. Acceptance tests

The spread gate remains open until credentialed evidence demonstrates:

- historical quote endpoint coverage for representative dates and delisted names where applicable;
- timestamps/sequence behavior are stable;
- deterministic panel acquisition is reproducible;
- all four liquidity buckets reach the minimum calibration count before acceptance testing;
- no future target enters an earlier model fit;
- predicted spread can be reconstructed from immutable manifests;
- the 35 bps rule is applied to the prior-close prediction, never the next-day realized spread.

## 10. Current gate

**IMPLEMENTATION PASS / CALIBRATION CONDITIONAL**

No observed historical quote calibration has been claimed because no quote provider has yet passed the license, cost, coverage, and credentialed-data gate.

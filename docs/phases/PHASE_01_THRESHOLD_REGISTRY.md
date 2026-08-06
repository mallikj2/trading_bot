# Phase 01 — Threshold Registry

**Strategy:** `CSMOM-LS-v0.2`  
**Status:** Frozen with Phase 01 approval

This registry prevents unexplained thresholds and silent post-result tuning. A change requires a new strategy version and decision record.

| Threshold | Primary value | Rationale | Required data | Principal leakage/quality risk | Test method | Rejection evidence |
|---|---:|---|---|---|---|---|
| Minimum adjusted close | USD 10 | Avoid penny-stock mechanics and whole-share noise | Point-in-time adjusted close | Bad split adjustment | Boundary and split tests | Edge exists only below threshold |
| Minimum market cap | USD 2B | Favor borrowable, liquid, institutionally traded names | Point-in-time market cap | Current values backfilled historically | Historical snapshot validation | Result collapses with valid point-in-time values |
| Minimum ADV60 | USD 25M | Keep small-account fills immaterial to volume | Raw close and raw volume | Adjusted price × raw volume error | Split-invariance test | Costs/capacity fail despite threshold |
| Minimum history | 300 sessions | Support 252-session feature plus validation buffer | Exchange calendar and bars | Counting missing/non-sessions as history | Calendar continuity tests | Too many symbols lack valid history |
| Recent momentum skip | 21 sessions | Reduce immediate reversal/event sensitivity | Adjusted close | Off-by-one indexing | Exact formula unit test | Nearby skip variants all fail |
| Long momentum lookback | 252 sessions | Standard intermediate horizon | Adjusted close | Survivorship and adjustment revisions | Formula/leakage tests | No stable OOS edge |
| Shorter momentum lookback | 126 sessions | Add medium-horizon confirmation | Adjusted close | Same as above | Formula/ablation tests | Component adds no stable value |
| Composite weights | 60% / 40% | Favor longer horizon while requiring confirmation | Cross-sectional features | Selection after seeing results | Frozen OAT grid | Simpler 12-1 baseline is better |
| Winsorization | 2.5% / 97.5% | Limit outlier influence without trimming many names | Cross section | Small/unrepresentative universe | Outlier and nearby stress | Result depends on extremes |
| Robust scale | 1.4826 × MAD | Robust normal-consistent scale | Cross section | Zero MAD | Zero-MAD fail-closed test | Frequent invalid cross sections |
| Minimum cross section | 20 | Avoid unstable ranking/scale | Valid eligible names | Survivorship/data gaps | 19/20 boundary tests | Too many dates fail closed |
| Score threshold | abs 0.75 | Require material cross-sectional separation | Composite score | Tuned threshold | Inclusive-boundary and OAT grid | Edge only at one exact value |
| SMA trend | 200 sessions | Absolute directional confirmation | Adjusted close | Off-by-one and revisions | Exact rolling test, ablation | Filter adds no stable value |
| VOL20 cap | 80% annualized | Avoid extreme idiosyncratic event risk | Adjusted returns | Bad corporate-action adjustment | Boundary/event tests | Tail loss still unacceptable |
| Position count | 3 per side | Small-account simplicity and concentration balance | Candidate ranks | One-side scarcity | Non-vacuous and scarcity tests | Whole-share diversification fails |
| Single-name cap | 20% | Prevent one position dominating | Target weights | Redistribution error | Weight-cap tests | Trade concentration breaches |
| Target side gross | 50% | Keep gross at or below 100% | Target weights | Confusing short proceeds with free leverage | Matched-gross test | Account constraints cannot support |
| Post-rounding net cap | 10% | Bound whole-share directional drift | Prices, shares, equity | High-priced names | Whole-share repair test | Frequent infeasible allocations |
| Same-sector cap | 2 per side | Reduce obvious industry clustering | Point-in-time sector | Current classifications backfilled | Deterministic selection tests | Residual sector concentration excessive |
| Correlation lookback | 60 sessions | Approximate current co-movement | Adjusted returns | Insufficient overlap | Pairwise history tests | Filter unstable or ineffective |
| Correlation minimum overlap | 50 sessions | Avoid unreliable pair estimates | Adjusted returns | Missing data | 49/50 boundary test | Too many candidates rejected |
| Correlation cap | abs 0.85 | Block near-duplicates | Adjusted returns | Regime instability | Boundary and ablation | Concentration remains or edge vanishes |
| Minimum hold | 10 sessions | Reduce churn and match swing horizon | Position state | Exit suppression bugs | Priority tests | Cost remains excessive |
| Maximum hold | 63 sessions | Bound stale positions | Position state/calendar | Off-by-one session age | 62/63 tests | Edge requires indefinite holding |
| Rank-buffer exit | top/bottom 30% | Avoid replacing on small rank changes | Daily ranks | Percentile/tie ambiguity | Boundary/tie tests | Turnover or decay unacceptable |
| Decision delay | 30 minutes after official close | Permit final-bar validation and handle early closes | Official calendar close | Hard-coded 16:00 close | Early-close test | Vendor finality needs longer delay |
| Fill window | 10:00–10:30 ET | Avoid opening auction and fix reproducible benchmark | Intraday bars/quotes | Missing or revised intraday bars | Window/expiry tests | Edge depends on unavailable fills |
| Maximum spread | 35 bps | Exclude expensive names | Point-in-time quotes/model | Using current spreads historically | Cost-stress test | Net edge consumed by spread |
| Unexplained daily move | 20% absolute | Detect data/event anomalies | Raw and adjusted bars/events | Split misclassification | Corporate-action tests | Frequent false blocks or tail failures |
| SPY daily stress | 5% absolute | Avoid initiating during extreme shock | SPY point-in-time data | Same-day timing misuse | Timestamp and stress tests | Rule adds no resilience |
| SPY VOL20 stress | 40% annualized | Avoid new risk in severe volatility | SPY returns | Look-ahead regime labels | Point-in-time test | Rule fails to reduce tail risk |
| Earnings entry rule | no event inside planned minimum hold | Avoid initiating into known binary event | Point-in-time earnings calendar | Backfilled schedules | Timestamp revision tests | Missing calendars invalidate test |
| Earnings exit timing | BMO/unknown prior day; AMC event day | Avoid intentional earnings hold | Point-in-time event timing | Late revisions | BMO/AMC/unknown cases | Operationally infeasible |
| Base Sharpe | 0.75 | Require meaningful risk-adjusted evidence | Net daily returns | Selection/multiple testing | Walk-forward/bootstrap | Below threshold |
| Pessimistic Sharpe | 0.50 | Require cost robustness | 2× cost returns | Understated costs | Cost stress | Below threshold |
| Maximum drawdown | 10% or stricter mandate | Capital preservation | Net equity curve | Marking/fill errors | Drawdown reconciliation | Above limit |
| Positive-year fraction | 60% | Require temporal breadth | OOS annual results | Partial-year handling | Calendar-year report | Below threshold |
| Nearby-positive fraction | 70% | Reject narrow optimum | Frozen OAT grid | Cherry-picking variants | Experiment registry | Below threshold |

## Change control

Any change to a primary value requires:

1. a new strategy version;
2. rationale recorded before examining the new final test;
3. an experiment-registry entry;
4. updated tests where applicable;
5. a decision record identifying whether the old strategy was rejected or merely superseded.

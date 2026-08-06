# Phase 01 — Strategy Research Specification

**Project:** Quant Trading Bot — Professional Trading Platform  
**Strategy:** `CSMOM-LS-v0.2`  
**Document version:** 0.2  
**Date:** 2026-08-05  
**Depends on:** Approved Trading Mandate v0.2  
**Supersedes:** `CSMOM-LS-v0.1` draft  
**Phase status:** CONDITIONAL PASS — awaiting explicit approval

---

## 1. Purpose

This phase freezes one simple, deterministic, falsifiable strategy hypothesis before historical results are examined. It defines the strategy-level contract that later data, backtest, risk, execution, and reliability phases must implement.

This document does not claim profitability, authorize live trading, select a production data vendor, or permit live short selling.

---

## 2. Inherited mandate

The strategy inherits Trading Mandate v0.2 without changing it.

- Initial development-capital reference: approximately USD 1,000.
- Limited-live capital may be approximately USD 5,000.
- Preferred live broker: Schwab.
- Account type: undecided.
- Long-and-short research is required.
- Preferred horizon: swing and position.
- Positions may remain overnight.
- The platform runs locally and must fail closed.
- Live decisions must be deterministic and version controlled.
- An LLM may assist research and explanation but may not authorize or submit live orders.

Any Phase 00 risk limit not repeated here remains authoritative.

### 2.1 Short-selling gate

The short sleeve is authorized for research only. Paper or live short orders remain prohibited until the later broker/account gate verifies:

1. a margin-enabled account;
2. account-level short permission;
3. symbol-level borrow availability;
4. borrow fee or conservative fee estimate;
5. locate/confirmation behavior where applicable;
6. recall, buy-in, dividend-liability, and reconciliation handling.

A long-only ablation is required but is not an automatic replacement for the approved long-short mandate.

---

## 3. Falsifiable investment hypothesis

Among sufficiently liquid US common stocks, securities with strong intermediate-term returns tend to outperform securities with weak intermediate-term returns over the following several weeks, after excluding the most recent month and after conservative trading, borrow, dividend, and financing costs.

The strategy combines 12-minus-1-month and 6-minus-1-month cross-sectional momentum, confirms the direction with a 200-session moving average, and holds a matched-gross portfolio of the strongest and weakest qualifying securities.

### 3.1 Proposed persistence mechanisms

Possible mechanisms include slow information diffusion, anchoring, gradual institutional rebalancing, benchmark constraints, and limits to arbitrage. These are explanations to test, not assumed facts.

### 3.2 Expected failure conditions

The strategy should be rejected when any of the following is observed:

- the net edge disappears after conservative costs;
- results depend on current constituents or revised data;
- the short sleeve depends on unavailable or uneconomic borrow;
- a few trades, years, symbols, or regimes explain most profit;
- nearby parameters fail;
- a one-session entry delay destroys the result;
- whole-share implementation at USD 5,000 destroys neutrality or diversification;
- the full strategy cannot beat the simpler preregistered momentum baseline.

---

## 4. Exact trading mandate

| Item | Frozen rule |
|---|---|
| Strategy ID | `CSMOM-LS-v0.2` |
| Asset class | US-listed common equities |
| Primary exchanges | NYSE and Nasdaq |
| Exclusions | OTC, preferreds, warrants, rights, units, closed-end funds, ETFs, leveraged/inverse products, options, and unresolved instrument histories |
| Stable identity | Internal `instrument_id`; ticker is display metadata only |
| Minimum adjusted close | USD 10.00 |
| Minimum point-in-time market capitalization | USD 2.0 billion |
| Minimum 60-session median raw dollar volume | USD 25 million |
| Minimum valid history | 300 exchange sessions |
| Universe refresh | Monthly, frozen after the final validated close of the prior month |
| Entry review | First eligible trading session of each week |
| Exit review | Every validated trading-session close |
| Decision timestamp | Official exchange close plus 30 minutes |
| Primary research fill benchmark | Next-session 10:00–10:30 America/New_York VWAP |
| Target expiry | 10:30 America/New_York on the next eligible session |
| Minimum hold | 10 sessions, except mandatory risk/data/event exits |
| Maximum hold | 63 sessions |
| Maximum positions | 3 long and 3 short |
| Target side gross | Up to 50% long and 50% short |
| Maximum single-name weight | 20% absolute |
| Maximum net exposure after target construction | 0% by design before rounding |
| Maximum net exposure after whole-share rounding | 10% of equity |
| Maximum same-sector names | 2 per side |
| Turnover | No forced filling; rank buffer and minimum hold reduce churn |
| Overnight exposure | Required |
| Pre/after-hours trading | Prohibited |
| Fractional shares | Not assumed |
| Live shorting | Prohibited pending later authorization |

### 4.1 Monthly universe timing

The universe effective for month `M` is computed only from records available after the final official close of month `M-1`, plus the configured data-finality delay. Later revisions may not rewrite an already frozen research universe without creating a new data version.

### 4.2 Weekly entries and daily exits

New positions and discretionary replacements are considered only on the first eligible session of the week. Mandatory exits are evaluated daily after a validated close.

Daily exit evaluation prevents a weekly schedule from delaying known trend, event, data, borrow, or maximum-hold exits.

---

## 5. Data and feature definitions

Let:

- `A[i,t]` be adjusted close;
- `C[i,t]` be raw close;
- `V[i,t]` be raw share volume;
- `r[i,t] = ln(A[i,t] / A[i,t-1])`.

All fields must be point-in-time and available no later than the recorded source-availability timestamp.

### 5.1 Split-safe liquidity

`RawDollarVolume[i,t] = C[i,t] × V[i,t]`

`ADV60[i,t] = median(RawDollarVolume[i,t-59:t])`

Adjusted close must not be multiplied by raw volume. Raw close and raw volume are paired so an ordinary split does not create an artificial liquidity jump.

### 5.2 Momentum

`MOM12_1[i,t] = ln(A[i,t-21] / A[i,t-252])`

`MOM6_1[i,t] = ln(A[i,t-21] / A[i,t-126])`

The latest 21 sessions are excluded to reduce immediate-reversal and event-gap sensitivity.

### 5.3 Volatility and trend

`VOL20[i,t] = sqrt(252) × stdev(r[i,t-19:t])`

`SMA200[i,t] = mean(A[i,t-199:t])`

### 5.4 Cross-sectional normalization

Each raw momentum feature is winsorized at the 2.5th and 97.5th percentiles on decision date `t`.

`z(x[i,t]) = (x_wins[i,t] - median(x_wins[:,t])) / (1.4826 × MAD(x_wins[:,t]))`

If the scaled MAD is zero, non-finite, or fewer than 20 eligible instruments remain, the date fails closed and no new target is produced.

### 5.5 Composite score

`SCORE[i,t] = 0.60 × z(MOM12_1[i,t]) + 0.40 × z(MOM6_1[i,t])`

These weights are frozen before testing.

---

## 6. Candidate rules

### 6.1 Long candidate

A security is a long candidate only when all conditions hold:

- `SCORE >= 0.75`;
- `MOM12_1 > 0`;
- `MOM6_1 > 0`;
- adjusted close is above `SMA200`;
- all universe, data, event, liquidity, concentration, and operational filters pass.

Select in descending score order, then ascending stable `instrument_id` for deterministic ties.

### 6.2 Short candidate

A security is a short research candidate only when all conditions hold:

- `SCORE <= -0.75`;
- `MOM12_1 < 0`;
- `MOM6_1 < 0`;
- adjusted close is below `SMA200`;
- all universe, data, event, liquidity, concentration, and operational filters pass.

Select in ascending score order, then ascending stable `instrument_id` for deterministic ties.

Executable paper/live shorts additionally require current borrow authorization. Historical research must not treat missing borrow observations as free and available.

### 6.3 Sector selection

Candidates are processed in rank order. A candidate is skipped when accepting it would create more than two names from the same sector on that side. The selector continues down the ranked list rather than force-filling a blocked symbol.

### 6.4 Correlation selection

Before accepting a new same-side candidate, calculate Pearson correlation from the most recent 60 adjusted daily log returns, requiring at least 50 overlapping observations.

- Reject the candidate if absolute correlation exceeds 0.85 with any already accepted same-side candidate.
- Reject the candidate if fewer than 50 overlapping observations exist.
- The first candidate on a side is not subject to pairwise correlation rejection.

This filter is part of the strategy contract. The supplied focused module receives its result through the fail-closed `entry_blocked` field; the point-in-time correlation join is implemented in Phase 02 data/feature integration.

---

## 7. Portfolio construction

### 7.1 Matched side gross

Let:

- `N_L` be the number of accepted longs;
- `N_S` be the number of accepted shorts;
- per-name cap be 20%;
- desired side gross be 50%.

The feasible gross assigned to each side is:

`G = min(0.50, 0.20 × N_L, 0.20 × N_S)`

If either side has zero accepted candidates, no new paired target portfolio is produced. The strategy may hold cash rather than create unintended market direction.

Examples:

- 3 longs and 3 shorts: up to 50% each side;
- 3 longs and 1 short: 20% each side;
- 3 longs and 0 shorts: no new target.

### 7.2 Within-side weights

For each accepted security:

`u[i] = 1 / max(VOL20[i], 0.10)`

Normalize `u` within each side to side gross `G`, cap each name at 20%, and iteratively redistribute residual weight among uncapped names.

Long weights are positive and short weights are negative. Continuous targets must sum to zero within numerical tolerance.

### 7.3 USD 5,000 whole-share feasibility

For the explicit small-account simulation:

1. compute `floor(abs(target_weight) × equity / reference_price)` shares;
2. never add a share above the continuous target;
3. calculate signed market value using the primary fill reference price;
4. if net exposure exceeds 10% of equity, remove one share at a time from the larger side;
5. choose the removal producing the smallest absolute resulting net exposure, with `instrument_id` as the tie-break;
6. reject the allocation if either side becomes zero or net exposure remains above 10%.

Residual cash is allowed and is reported.

---

## 8. Entry, fill, expiry, and exit rules

### 8.1 Decision time and early closes

The decision timestamp is always relative to the official exchange close:

`decision_timestamp = official_session_close + 30 minutes`

Therefore a 13:00 early close produces a 13:30 decision timestamp; the strategy does not hard-code 16:15 or 16:30.

### 8.2 Primary entry and discretionary-exit benchmark

The final acceptance backtest must use next-session 10:00–10:30 ET VWAP calculated from validated intraday bars, plus explicit adverse trading costs.

- Bar interval: five minutes or finer.
- VWAP window: 10:00 inclusive to 10:30 exclusive.
- Missing, suspect, halted, or incomplete window: no fill.
- No fill by 10:30: target expires and may not be carried forward.
- A fresh decision is required for a later session.

A next-open proxy may be used only for preliminary engineering tests and may not support final acceptance.

### 8.3 Entry rule

On the first eligible weekly entry review:

1. freeze the valid monthly universe;
2. calculate features after the finality delay;
3. apply all fail-closed filters;
4. retain eligible positions unless an exit is due;
5. rank and select candidates deterministically;
6. construct matched-gross targets;
7. apply whole-share feasibility for the USD 5,000 report;
8. emit versioned target records for the next session;
9. expire unfilled targets at 10:30.

### 8.4 Exit hierarchy

The first applicable rule wins:

1. independent risk, kill-switch, or reconciliation exit;
2. data, delisting, corporate-action, broker, or borrow invalidation;
3. scheduled earnings exit;
4. maximum 63-session hold;
5. trend invalidation: long below `SMA200`, short above `SMA200`;
6. score invalidation: long score below 0, short score above 0;
7. after the 10-session minimum hold, rank-buffer exit: long outside top 30%, short outside bottom 30%;
8. after the minimum hold, weekly replacement by a stronger valid candidate, subject to turnover and constraints.

A mandatory exit is not suppressed by the minimum holding period.

### 8.5 Earnings policy

The strategy does not intentionally hold through scheduled earnings.

- **Before-open or unknown-time event:** exit during the prior session's 10:00–10:30 window.
- **After-close event:** exit during the event session's 10:00–10:30 window.
- **During-session event:** treat as before-open and exit the prior session.
- **New entries:** blocked when the planned minimum holding interval would include a scheduled earnings event.
- **Re-entry:** allowed only from a decision made after the event session's validated close.
- **Late schedule revision:** mark an operational exception, prohibit adding, and issue the next available mandatory exit; do not rewrite history.

Historical calendars must preserve the timestamp at which each schedule was known. Current calendars cannot be backfilled into historical tests.

---

## 9. Do-not-trade rules

No new position is produced when any applicable rule is true.

### 9.1 Data and identity

- missing or duplicate stable instrument key;
- incomplete, stale, suspect, or rejected bar;
- unresolved symbol/listing history;
- unknown corporate-action adjustment;
- non-finite feature;
- fewer than 300 valid sessions;
- fewer than 20 valid cross-sectional observations;
- zero or non-finite cross-sectional MAD;
- missing point-in-time market capitalization;
- version mismatch among data, universe, feature, strategy, and code commit.

### 9.2 Liquidity and price

- adjusted close below USD 10;
- `ADV60` below USD 25 million;
- final modeled spread above 35 basis points;
- intended order above the later approved participation cap;
- halt, limit state, or unresolved exchange restriction.

### 9.3 Symbol and market stress

- `VOL20 > 80%` annualized;
- unexplained absolute one-session raw return above 20%;
- SPY absolute one-session return above 5%;
- SPY 20-session annualized realized volatility above 40%.

During market stress, no new positions are opened. Existing positions remain under the daily exit and independent risk rules.

### 9.4 Events

- scheduled earnings conflict;
- unresolved merger, tender, spinoff, bankruptcy, symbol change, or material corporate action;
- event timestamp unavailable or not point-in-time reliable.

### 9.5 Concentration and neutrality

- more than two names from one sector on a side;
- same-side absolute correlation above 0.85 with any accepted position;
- fewer than 50 overlapping correlation observations;
- gross, net, single-name, or mandate constraint breach;
- whole-share allocation cannot keep both sides populated and net exposure within 10%.

### 9.6 Short-specific

For executable paper/live shorting:

- account/environment not authorized;
- borrow state unknown or unavailable;
- hard-to-borrow under configured policy;
- borrow cost estimate missing;
- recall, buy-in, or broker restriction active;
- dividend liability cannot be estimated;
- locate/confirmation cannot be associated with the order.

### 9.7 Operational

- broker and local state disagree;
- market calendar or official close is uncertain;
- clock synchronization fails;
- database/journal write fails;
- configuration or secret validation fails;
- kill switch, halt state, or manual-review state is active.

---

## 10. Baselines and ablations

All results must include:

1. cash/zero-return baseline;
2. SPY total return for market context;
3. equal-weight eligible-universe long-only, monthly;
4. simple three-name long-only 12-minus-1 momentum;
5. simple three-long/three-short matched-gross 12-minus-1 momentum;
6. one-month mean-reversion baseline;
7. no-trend-filter ablation;
8. equal-weight instead of inverse-volatility ablation;
9. `MOM12_1`-only ablation;
10. `MOM6_1`-only ablation;
11. randomized symbol-rank controls preserving dates and position counts;
12. circularly shifted signal controls;
13. one-session delayed-entry stress;
14. long-only implementation ablation;
15. no-earnings-exit ablation for attribution only, not as the production candidate.

The simpler market-neutral 12-minus-1 baseline is preferred if the composite cannot add stable out-of-sample value.

---

## 11. Frozen statistical design inputs

### 11.1 Primary return series

Use daily marked-to-market net portfolio returns. Cash earns zero in the primary analysis. Financing assumptions are reported separately.

### 11.2 Metric formulas

- **Annualized return:** geometric annualization from daily net returns using 252 sessions.
- **Sharpe:** `sqrt(252) × mean(daily_net_return) / stdev(daily_net_return)`, risk-free rate zero.
- **Sortino:** `sqrt(252) × mean(daily_net_return) / downside_deviation`, where downside deviation uses returns below zero.
- **Maximum drawdown:** largest peak-to-trough decline in compounded net equity.
- **Calmar:** annualized net return divided by absolute maximum drawdown.
- **Profit factor:** sum of positive completed-position net P&L divided by absolute sum of negative completed-position net P&L.
- **Trade expectancy:** mean completed-position net P&L divided by allocated entry notional, in basis points.
- **Weekly expected shortfall 95%:** arithmetic mean of the worst 5% of non-overlapping Friday-to-Friday net returns.
- **Gross turnover:** sum of absolute traded notional divided by beginning-of-day equity; monthly turnover is the sum across sessions.

### 11.3 Frozen one-parameter-at-a-time sensitivity grid

Only one item changes from the primary configuration at a time:

- score threshold: `0.50`, `0.75`, `1.00`;
- momentum weights: `1.00/0.00`, `0.75/0.25`, `0.60/0.40`, `0.50/0.50`;
- minimum hold: `5`, `10`, `15` sessions;
- maximum hold: `42`, `63`, `84` sessions;
- rank-buffer exit percentile: `20%`, `30%`, `40%`.

The primary value is included in each line and is not double-counted when calculating nearby variants. No parameter is selected from the final untouched period.

### 11.4 Frozen market regimes

Regimes use point-in-time SPY adjusted close, `SMA200`, and `VOL20`:

1. **Transition:** `abs(SPY / SMA200 - 1) <= 2%`.
2. **Bull low-vol:** above the transition band and `VOL20 < 20%`.
3. **Bull high-vol:** above the transition band and `VOL20 >= 20%`.
4. **Bear low-vol:** below the transition band and `VOL20 < 20%`.
5. **Bear high-vol:** below the transition band and `VOL20 >= 20%`.

Each regime must contain at least 26 out-of-sample weekly observations to count toward the regime acceptance test.

---

## 12. Preregistered acceptance criteria

### 12.1 Minimum evidence

- at least 10 calendar years where valid point-in-time data permit;
- at least 200 completed position trades;
- at least 100 out-of-sample weekly decisions;
- at least 26 out-of-sample weekly observations in each regime used for the regime test.

Insufficient evidence prevents an unconditional pass.

### 12.2 Base-cost performance

- annualized net return greater than 0%;
- Sharpe at least 0.75;
- Sortino at least 1.00;
- Calmar at least 0.75;
- profit factor at least 1.20;
- average trade expectancy at least 10 basis points net.

### 12.3 Pessimistic costs

With all spread, slippage, fees, borrow, dividend, and financing costs multiplied by 2:

- annualized net return remains greater than 0%;
- Sharpe remains at least 0.50;
- profit factor remains above 1.05.

### 12.4 Drawdown and concentration

- maximum drawdown no worse than 10% and within any stricter Phase 00 limit;
- weekly expected shortfall 95% no worse than -3.0%;
- no one completed trade contributes more than 20% of total net profit;
- removing the five best trades leaves cumulative net return positive;
- no one year contributes more than 35% of cumulative net profit.

### 12.5 Stability

- at least 60% of out-of-sample calendar years are net positive;
- net return is positive in at least three of the five frozen regimes;
- median walk-forward out-of-sample Sharpe is at least 0.50;
- at least 70% of frozen nearby variants have positive net return;
- median nearby-variant Sharpe is at least 0.40;
- a one-session entry delay does not reduce cumulative net profit by more than 50%;
- USD 5,000 whole-share simulation remains net profitable and respects the 10% net-exposure limit.

### 12.6 Baseline superiority

The full strategy must either:

- exceed the simple market-neutral 12-minus-1 baseline's net Sharpe by at least 0.10; or
- reduce maximum drawdown by at least 20% without reducing annualized net return by more than 10%.

It must also exceed the 95th percentile of randomized-control net performance.

### 12.7 Statistical reporting

Phase 03 must report:

- stationary or moving-block bootstrap confidence intervals;
- exact hypothesis and variant counts;
- dependence-aware uncertainty;
- multiple-testing-aware Sharpe assessment where appropriate;
- pre-cost and post-cost results;
- long and short sleeve results separately;
- earnings, borrow, and whole-share attribution.

---

## 13. Data contracts

### 13.1 Daily bar

Required fields:

- `instrument_id`;
- `symbol`;
- `session_date`;
- raw OHLC and raw volume;
- adjusted close and adjustment version;
- source-availability timestamp;
- ingestion timestamp;
- data version;
- quality status.

### 13.2 Instrument snapshot

- stable instrument ID;
- symbol and primary exchange;
- security type;
- listing status;
- sector and industry;
- point-in-time market capitalization;
- effective-from/effective-to timestamps;
- source and version.

### 13.3 Corporate action

- instrument ID;
- action type;
- ex/effective date and timestamp;
- adjustment factors and cash amounts;
- source-availability timestamp;
- revision/version;
- validation status.

### 13.4 Earnings event

- instrument ID;
- scheduled event timestamp;
- before-open/after-close/during-session/unknown classification;
- timestamp at which schedule became known;
- revision/version;
- confidence status.

### 13.5 Borrow observation

- instrument ID;
- broker/account/environment;
- observation and expiry timestamps;
- available/unknown/unavailable state;
- hard-to-borrow state;
- estimated rate/fee;
- locate or confirmation identifier where applicable.

### 13.6 Signal and target record

- strategy ID/version;
- decision timestamp;
- stable instrument ID;
- data, universe, feature, and code versions;
- feature values and score;
- all eligibility outcomes and abstention reasons;
- target weight and whole-share result;
- execution-window start and expiry;
- deterministic tie-break key.

---

## 14. Research flow

```text
Immutable point-in-time data
          |
          v
Identity, calendar, action and quality validation
          |
     +----+----+
     |         |
   FAIL       PASS
     |         |
 No target   Frozen monthly universe
               |
               v
     Split-safe liquidity + momentum features
               |
               v
       Robust cross-sectional scoring
               |
               v
 Event, stress, sector, correlation filters
               |
               v
       Deterministic long/short ranking
               |
               v
          Matched side gross
               |
               v
     Continuous and USD 5,000 targets
               |
               v
 Next-session 10:00–10:30 expiring intent
               |
               v
 Independent risk and execution phases
```

---

## 15. Reference implementation scope

The repository files implement and test:

- stable instrument-key validation;
- raw-close/raw-volume liquidity;
- momentum, volatility, and trend features;
- robust cross-sectional normalization;
- non-vacuous candidate selection;
- deterministic threshold and tie behavior;
- sector limits;
- matched long/short gross exposure;
- whole-share neutrality repair;
- relative-to-close decision timestamps;
- expiring target records;
- YAML/runtime configuration consistency;
- future-data leakage resistance.

The focused module intentionally does not implement data-vendor ingestion, point-in-time event joins, the backtest engine, realistic cost simulation, broker APIs, the independent risk engine, or live order handling.

---

## 16. Failure modes and required response

| Evidence | Required response |
|---|---|
| No net out-of-sample edge | Reject strategy |
| Edge disappears after base costs | Reject strategy |
| Edge disappears at 2x costs | Reject or redesign; no approval |
| Current-constituent or revised-data dependency | Invalidate affected test |
| Future data change past signals | Critical leakage defect |
| Borrow unavailable/uneconomic | Reject or redesign short sleeve |
| Full model fails to beat simple baseline | Prefer simpler baseline |
| Nearby variants fail | Reject as unstable/overfit |
| One regime or year dominates | Reject or narrow only with new mandate approval |
| USD 5,000 allocation fails | Reject operational suitability or redesign |
| Safe shorting cannot be authorized | Keep shorts out of live trading |
| Required point-in-time event data unavailable | Do not run final acceptance test |

---

## 17. Alternatives considered

### Long-only trend/momentum

Operationally simpler and compatible with a cash account. Retained as an ablation and possible limited-live predecessor, but not selected as the sole research candidate because the mandate requires long-and-short research.

### Intraday mean reversion

Deferred because it creates materially higher data, latency, spread, availability, and laptop-operability burden and does not match the preferred swing/position horizon.

### Fundamental-quality plus momentum

Deferred until a price-only hypothesis survives. Point-in-time filings, restatements, and vendor costs add leakage and complexity.

### Machine-learning ranker

Rejected for the first strategy because no simple edge has yet been demonstrated and the overfitting/governance burden is higher.

---

## 18. Decision record

**Decision ID:** `DR-P01-002`  
**Decision:** Propose `CSMOM-LS-v0.2` as the first frozen strategy research candidate.  
**Supersedes:** incomplete `CSMOM-LS-v0.1` draft.  
**Scope:** research specification only.  
**Live implication:** none.  
**Revisit triggers:** failed acceptance criteria, unavailable point-in-time data, impractical whole-share behavior, inability to authorize safe shorts, or failure to beat the simple baseline.

---

## 19. Phase gate

### Status: CONDITIONAL PASS

Phase 01 becomes PASS only after:

1. explicit approval of `CSMOM-LS-v0.2`;
2. commit of this specification, threshold registry, acceptance gate, YAML, implementation, tests, and executed test evidence;
3. update of canonical project state and decisions;
4. confirmation that acceptance criteria will not be changed after observing final results without a new version and decision record.

The undecided account type and unverified short capability do not block Phase 02 data/statistical design, but remain hard blockers for live short orders.

---

## 20. Next three tasks

1. Approve or reject `CSMOM-LS-v0.2`.
2. In Phase 02, define point-in-time data tiers, historical universe reconstruction, event/borrow limitations, and walk-forward split policy.
3. Create the immutable experiment registry before running any strategy backtest.

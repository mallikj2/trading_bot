# Phase 02 — Phase 01 Reconciliation

**Project:** Quant Trading Bot — Professional Trading Platform  
**Strategy:** `CSMOM-LS-v0.2`  
**Document version:** 0.1  
**Date:** 2026-08-05  
**Depends on:** Trading Mandate v0.2 and approved Phase 01 strategy specification v0.2  
**Result:** PASS — reconciliation complete  
**Phase 02 result:** Not yet evaluated

---

## 1. Objective

Translate every approved Phase 01 strategy rule into an explicit Phase 02 data, timing, lineage, availability, quality, and fail-closed requirement.

This document resolves differences between the initial generic Phase 02 design and the actual approved strategy. It does not change the strategy's frozen values.

---

## 2. Authority and approval normalization

The source bundle's Phase 01 files were generated while owner approval was still pending and therefore contain `PROPOSED` or `CONDITIONAL PASS` status text. The owner subsequently issued the required approval phrase:

```text
APPROVE STRATEGY SPEC V0.2
```

The authoritative project state is therefore:

- Phase 00: PASS.
- Trading Mandate v0.2: APPROVED — LOCKED.
- Phase 01: PASS.
- `CSMOM-LS-v0.2`: APPROVED as the frozen first research candidate.
- Phase 02: ACTIVE.
- Paper/live order submission: NOT AUTHORIZED.
- Live shorting: PROHIBITED pending later gates.

The original approved artifacts remain immutable evidence. Canonical state and decision files should record the later approval rather than rewriting the historical bundle.

---

## 3. Reconciliation result

### 3.1 No mandate conflict

The strategy remains within the Phase 00 research mandate:

- U.S.-listed common equities.
- NYSE and Nasdaq.
- Long-and-short research.
- Swing/position horizon.
- Low-frequency decisions.
- Overnight exposure.
- No initial live shorting or leverage.

SPY is required only as a benchmark, stress indicator, and regime reference. It is not part of the tradable strategy universe and does not violate the strategy's ETF exclusion.

### 3.2 Material corrections to the generic Phase 02 draft

| Area | Generic Phase 02 assumption | Approved Phase 01 requirement | Reconciled rule |
|---|---|---|---|
| Tradable universe | Common equities and possibly selected ETFs | NYSE/Nasdaq common stocks only; ETFs excluded | Exclude ETFs from targets; retain SPY as a reference instrument only |
| Minimum price | USD 5 raw close | USD 10 adjusted close | Use point-in-time/as-of adjusted close at the monthly universe freeze |
| Market size | Not required | Point-in-time market cap at least USD 2B | Mandatory monthly universe field |
| Liquidity | 63-session median dollar volume of USD 5M | 60-session median raw dollar volume of USD 25M | Freeze exact Phase 01 formula and threshold |
| History | 252 sessions | 300 valid exchange sessions | Require 300 valid sessions |
| Universe cadence | Daily reconstruction | Monthly frozen universe | Build after final validated prior-month close plus 30 minutes; apply for the next month |
| Entry cadence | Generic next-session execution | Weekly review on first eligible session | Decision after first eligible weekly session close; target next session |
| Exit cadence | Not fully reconciled | Daily validated-close exit review | Generate mandatory/discretionary exit intents daily according to hierarchy |
| Fill benchmark | Next open or generic next session | Next-session 10:00–10:30 ET VWAP | Validated intraday VWAP is mandatory for final acceptance |
| Intraday data | Initially unnecessary | Five-minute or finer bars for fill benchmark | Intraday data is required for execution simulation, not signal generation |
| Fundamentals | Disabled | Point-in-time market cap and sector are required | Full fundamental factors remain disabled; reference fundamentals are mandatory |
| Earnings | Could remain disabled | Revision-aware scheduled earnings policy is part of the strategy | Earnings schedule history is a hard final-backtest dependency |
| Historical spread | Scenario only | Final modeled spread must be no more than 35 bps | A deterministic, preregistered quote/spread model is mandatory |
| Borrow | Not known historically | Conservative borrow, dividend, recall, and short constraints required | Historical borrow may be modeled conservatively; missing borrow cannot be treated as free |
| Adjusted prices | Separate adjusted series | Adjusted close drives signals and price threshold | Adjustments must be as-of the decision date and may not include future actions |

---

## 4. Frozen strategy-to-data contract

### 4.1 Tradable instrument contract

An instrument can enter the frozen monthly universe only when all conditions are true at the universe freeze timestamp:

1. Stable `instrument_id` exists.
2. Listing is active on NYSE or Nasdaq.
3. Security type is `COMMON_STOCK`.
4. Instrument is not an ETF, preferred, warrant, right, unit, closed-end fund, OTC issue, or unresolved identity.
5. Point-in-time adjusted close is at least USD 10.
6. Point-in-time market capitalization is at least USD 2 billion.
7. Median 60-session raw dollar volume is at least USD 25 million.
8. At least 300 valid exchange sessions exist.
9. `VOL20` is no more than 80% annualized.
10. Market cap, sector, identity, corporate actions, and daily bars pass quality gates.

The monthly universe is frozen. Daily operational checks may still block entry or force exit for delisting, halt, action, event, data, or identity invalidation.

### 4.2 Signal contract

Required point-in-time features:

```text
RawDollarVolume[t] = RawClose[t] × RawVolume[t]
ADV60[t] = median(RawDollarVolume[t-59:t])
LogReturn[t] = ln(AdjustedClose[t] / AdjustedClose[t-1])
MOM12_1[t] = ln(AdjustedClose[t-21] / AdjustedClose[t-252])
MOM6_1[t] = ln(AdjustedClose[t-21] / AdjustedClose[t-126])
VOL20[t] = sqrt(252) × sample_stdev(LogReturn[t-19:t])
SMA200[t] = mean(AdjustedClose[t-199:t])
```

Cross-sectional calculation on each decision date:

1. Use only valid scored members of the frozen monthly universe.
2. Winsorize each momentum feature at 2.5% and 97.5%.
3. Scale by median and `1.4826 × MAD`.
4. Fail closed when fewer than 20 valid instruments remain or scale is non-positive/non-finite.
5. Calculate `SCORE = 0.60 × z(MOM12_1) + 0.40 × z(MOM6_1)`.

### 4.3 Reference and event contract

Required non-tradable/reference data:

- SPY daily as-of adjusted close and corporate actions.
- SPY `SMA200`, one-session return, and `VOL20`.
- Historical scheduled earnings records with `known_at`, event timestamp, timing class, revision, confidence, and cancellation state.
- Point-in-time sector classification.
- Intraday execution-window bars or trades.
- Historical quote data or an approved deterministic spread model.
- Cash dividends and other short liability events.

### 4.4 Return and terminal-event contract

Backtest-ready normalized data must support:

- Daily mark-to-market returns.
- Cash distributions.
- Splits and reverse splits.
- Mergers, acquisitions, spinoffs, symbol changes, relistings, and delistings.
- Terminal cash/stock consideration.
- Delisting returns or conservative terminal-value treatment when authoritative data are unavailable.
- Separate long- and short-sleeve attribution.

---

## 5. Deterministic Phase 02 interpretations

These rules remove implementation ambiguity before any Phase 03 results are observed. They do not change a Phase 01 threshold.

### R02-P01-01 — Month definition and universe freeze

- Calendar: official NYSE session calendar.
- Month: calendar month in `America/New_York`.
- Freeze session: final eligible NYSE session of the prior calendar month.
- Freeze timestamp: official close plus 30 minutes.
- Effective interval: first eligible session of the new month through its final eligible session.
- A later provider correction creates a new data version; it does not rewrite an existing frozen universe.

### R02-P01-02 — Week definition

- Week: ISO Monday-through-Sunday week in `America/New_York`.
- Weekly entry-review session: first eligible NYSE session in that week.
- Decision timestamp: that session's official close plus 30 minutes.
- Intended fill session: next eligible NYSE session.

### R02-P01-03 — Ten-session minimum hold

- The fill session counts as held session 1.
- The tenth eligible exchange session after and including the fill session is the minimum-hold completion session.
- A discretionary exit decision can first be made after the validated close of that tenth session and can first fill in the next eligible session's execution window.
- Mandatory exits remain exempt.
- An entry is blocked when the scheduled earnings policy would require an exit before the discretionary minimum-hold release.

### R02-P01-04 — Rank-buffer population and ties

- Population: all instruments with a valid daily score in the frozen monthly universe after applicable data/event/operational filters.
- Long ordering: score descending, then `instrument_id` ascending.
- Short ordering: score ascending, then `instrument_id` ascending.
- Buffer size: `max(1, ceil(0.30 × N))` for a valid population of size `N`.
- Long remains inside the buffer when ranked within the first buffer-size names in long order.
- Short remains inside the buffer when ranked within the first buffer-size names in short order.

### R02-P01-05 — As-of adjusted close

For a decision at time `τ`, adjusted close history may use only corporate actions whose effective and available timestamps are no later than `τ`.

A future split, dividend, spinoff, merger, or provider adjustment revision must not alter a historical feature in the same dataset version.

### R02-P01-06 — Point-in-time market capitalization

Canonical derivation when direct provider point-in-time market cap is unavailable:

```text
MarketCapPIT[t] = RawClose[t] × SharesOutstandingPIT[t]
```

`SharesOutstandingPIT[t]` is the most recent share-count observation whose `available_at` is no later than the universe freeze timestamp, adjusted only for corporate actions effective by `t`.

A vendor-provided market cap is acceptable only when its as-of and availability semantics are documented and validated. Current market cap may not be backfilled.

### R02-P01-07 — Intraday VWAP

For the next eligible session:

- Window: 10:00:00 inclusive to 10:30:00 exclusive, `America/New_York`.
- Granularity: five minutes or finer.
- Required coverage: contiguous complete window with no suspect/rejected intervals.
- Bar contract: interval start/end, volume, and interval VWAP; trade-level data may be aggregated instead.
- Window VWAP:

```text
VWAP = sum(IntervalVWAP[k] × IntervalVolume[k]) / sum(IntervalVolume[k])
```

- Zero volume, halt, missing interval, invalid timestamp, or incomplete coverage: no fill.
- Target expires at 10:30 and cannot roll forward.

A typical-price approximation is not the final acceptance benchmark unless separately approved as a new strategy version.

### R02-P01-08 — Earnings entry interval

For a proposed fill session `f`:

1. Calculate the minimum-hold completion session under R02-P01-03.
2. Convert each known earnings event into its required exit session:
   - before-open, during-session, or unknown time: prior eligible session;
   - after-close: event session.
3. Block entry when a required earnings exit session is on or before the minimum-hold completion session.
4. Use only the latest schedule revision known at the decision timestamp.

### R02-P01-09 — Unexplained daily move

```text
RawReturn[t] = RawClose[t] / RawClose[t-1] - 1
```

An absolute move above 20% is considered explained only when a validated corporate action or terminal event bridges the two sessions and the normalized action-adjusted return passes the configured data-quality checks. Otherwise, the instrument is blocked and quarantined for review.

---

## 6. Blocking Phase 02 data contracts

The reconciliation itself passes, but Phase 02 cannot pass and Phase 03 final acceptance cannot begin until these are resolved and tested:

| ID | Blocking contract | Why required |
|---|---|---|
| B02-01 | Point-in-time market capitalization source or derivation | Frozen USD 2B universe threshold |
| B02-02 | Point-in-time sector taxonomy and effective-history source | Maximum two names per sector per side |
| B02-03 | Revision-aware historical earnings schedule | Entry blocks and mandatory exits |
| B02-04 | Validated 10:00–10:30 intraday VWAP dataset | Frozen final fill benchmark |
| B02-05 | Historical spread/quote model preregistration | Frozen 35 bps do-not-trade rule and cost realism |
| B02-06 | Survivorship-aware identity, listing, delisting, and corporate actions | Historical universe and terminal returns |
| B02-07 | Conservative historical short-borrow and dividend-liability model | Short-side conclusion and pessimistic costs |

The selected solution must fit the mandate's initial recurring data-budget ceiling or receive an approved mandate amendment. One-time historical purchases and recurring subscriptions must be recorded separately.

---

## 7. Nonblocking items deferred to later phases

- Exact commission, slippage, market-impact, financing, and borrow-cost parameter values: Phase 03.
- Risk sizing and stop policy: Phase 04.
- Production database and service architecture: Phase 05.
- Schwab/Moomoo contract implementation: Phase 06.
- Live borrow checks and short-order workflow: Phase 06 and Phase 09.

The underlying raw and normalized data required to support these later tests must still be preserved in Phase 02.

---

## 8. Required reconciliation tests

1. All Phase 01 YAML runtime values map to a data-contract field or a strategy-only field.
2. No Phase 02 threshold conflicts with the Phase 01 threshold registry.
3. SPY can be loaded as a reference instrument without entering the tradable universe.
4. Future corporate actions do not change an earlier as-of adjusted price series.
5. Monthly universe membership is stable within a data version.
6. A current market-cap snapshot cannot pass a historical query.
7. A current sector value cannot be silently backfilled.
8. A revised earnings date is invisible before its `known_at` timestamp.
9. An incomplete VWAP window returns no fill.
10. A future intraday bar cannot enter the execution benchmark.
11. A missing or unapproved spread estimate blocks entry.
12. A delisted security remains in historical membership before its delisting.
13. Ticker reuse does not merge two instruments.
14. All reference, universe, feature, and target records carry lineage hashes.

---

## 9. Reconciliation gate

### PASS

The approved Phase 01 specification has been reconciled into exact Phase 02 requirements without changing frozen strategy thresholds.

This PASS is limited to the reconciliation task. It is not a Phase 02 PASS and does not authorize Phase 03 backtesting.

---

## 10. Next three tasks

1. Execute the provider proof of concept against B02-01 through B02-06.
2. Freeze the spread and short-borrow modeling contracts before any final acceptance backtest.
3. Implement the minimum Phase 02 data kernel and execute the point-in-time acceptance suite.

# CSMOM-LS-v0.2 — Data Requirements Matrix

**Version:** 0.1  
**Date:** 2026-08-05  
**Purpose:** Exact Phase 01-to-Phase 02 inventory

## Status definitions

- `REQUIRED`: required for the relevant Phase 02 normalized dataset.
- `BLOCKING`: unresolved provider or method contract that blocks Phase 02 PASS and final Phase 03 acceptance.
- `BLOCKING_FOR_SHORT_CONCLUSION`: the long-side pipeline may proceed, but an executable short-side conclusion cannot be approved without conservative treatment.

| ID | Role | Data/field | Frequency | Lookback | Transformation | Availability | Missing behavior | Required history | Source class | Leakage/quality test | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | Calendar | Official NYSE sessions, opens, closes, early closes | Session | N/A | Versioned session mapping | Known before dependent decisions | Block whole session | Full research period | Exchange-calendar source | Early-close/DST/holiday tests | REQUIRED |
| D02 | Identity | instrument_id, aliases, issuer and predecessor/successor links | Event/state | Full history | Bitemporal identity resolution | available_at <= decision_at | Block instrument | Full research period | Security master/reference provider | Ticker reuse and symbol-change tests | REQUIRED |
| D03 | Listing/universe | Exchange, listing status, security type, ETF flag | State/daily | Monthly freeze plus daily invalidation | Eligibility reason codes | At monthly freeze; daily status by decision | Exclude/block | Full research period including delisted | Survivorship-aware reference source | Delisted-before/after and current-list leakage tests | REQUIRED |
| D04 | Daily bars | Raw OHLC and raw share volume | Daily | 300+ valid sessions | Validate OHLC; RawClose × RawVolume | By close +30m decision | Block instrument/session | At least 10 calendar years where valid | Research EOD provider | Future-bar, split and duplicate tests | REQUIRED |
| D05 | Corporate actions | Splits, dividends, spinoffs, mergers, delistings | Event | Full identity history | Create as-of adjustment factors and terminal events | Effective and available by decision | Block affected instrument | Full research period | Corporate-action provider | Future-action and reconciliation tests | REQUIRED |
| D06 | Adjusted close | As-of split/total-return adjusted close | Daily | 252 sessions plus buffers | Apply only known/effective factors | By decision timestamp | Block feature | 300 valid sessions | Derived from D04/D05 or validated provider | Future split/dividend invariance test | REQUIRED |
| D07 | Market cap | PIT market cap or PIT shares outstanding | Monthly/state | Latest known at freeze | RawClose × SharesOutstandingPIT when derived | available_at <= monthly freeze | Exclude from universe | Research period | Reference/fundamental provider or SEC-derived | Current-value backfill rejection | BLOCKING |
| D08 | Sector | PIT sector code and taxonomy version | State | Effective interval at each decision | Bitemporal taxonomy join | available_at <= decision_at | Block entry | Research period | Historical classification source | Revision/effective-overlap tests | BLOCKING |
| D09 | Universe snapshot | Frozen monthly eligibility and reasons | Monthly | D02-D08 | Deterministic boolean filters | Prior-month close +30m | No membership | Every month | Derived | Rebuild/hash and no-midmonth-rewrite tests | REQUIRED |
| D10 | Liquidity | ADV60 | Daily/freeze | 60 sessions | median(RawClose × RawVolume) | Inputs known by decision | Exclude/block | 60 valid sessions; 300 overall | Derived | Split-safe liquidity test | REQUIRED |
| D11 | Returns | Adjusted daily log return | Daily | 1 prior session | ln(A[t]/A[t-1]) | Inputs known by decision | Null/block dependent feature | 300 valid sessions | Derived | No-future-row test | REQUIRED |
| D12 | Momentum | MOM12_1 | Daily | 252 with 21-session skip | ln(A[t-21]/A[t-252]) | Inputs known by decision | Null/block | 300 valid sessions | Derived | Exact-index/off-by-one test | REQUIRED |
| D13 | Momentum | MOM6_1 | Daily | 126 with 21-session skip | ln(A[t-21]/A[t-126]) | Inputs known by decision | Null/block | 300 valid sessions | Derived | Exact-index/off-by-one test | REQUIRED |
| D14 | Risk feature | VOL20 | Daily | 20 returns | sqrt(252) × sample stdev | Inputs known by decision | Null/block | 300 valid sessions | Derived | 19/20 boundary and action anomaly tests | REQUIRED |
| D15 | Trend | SMA200 | Daily | 200 closes | Arithmetic mean | Inputs known by decision | Null/block | 300 valid sessions | Derived | 199/200 boundary test | REQUIRED |
| D16 | Cross section | Winsorized robust z-scores and composite score | Decision date | At least 20 valid names | 2.5/97.5 winsor; median/MAD; 60/40 score | After daily inputs final | No new target | Every decision date | Derived | Zero-MAD, 19/20, deterministic tie tests | REQUIRED |
| D17 | Concentration | Same-side Pearson correlation | Decision date | 60 returns; at least 50 overlap | Pairwise Pearson on adjusted log returns | Inputs known by decision | Reject candidate | 60-session rolling | Derived | 49/50 and 0.85 boundary tests | REQUIRED |
| D18 | Market stress | SPY one-session return | Daily | 2 closes | A[t]/A[t-1]-1 | By decision | No new targets | Full period | Reference ETF data | Same-day/future-data test | REQUIRED |
| D19 | Market stress/regime | SPY VOL20 and SMA200 | Daily | 20/200 sessions | Phase 01 formulas and frozen regimes | By decision | No new target/regime null | Full period | Reference ETF data | Point-in-time regime test | REQUIRED |
| D20 | Events | Earnings schedule and revision history | Event/revision | Forward through minimum hold | Map timing to required exit session | known_at <= decision_at | Block entry/mandatory exit; missing blocks final test | Full research period | Revision-aware earnings provider | Late-revision/BMO/AMC/unknown tests | BLOCKING |
| D21 | Execution | Intraday interval VWAP and volume | <=5 minute | 10:00-10:30 next session | Volume-weight interval VWAPs | No future interval beyond simulated clock | No fill; expire target | Full acceptance test period | Intraday provider/trades | Completeness, halt, timestamp tests | BLOCKING |
| D22 | Liquidity/cost | Historical spread estimate | Decision/fill | Frozen method inputs | Observed quote or preregistered model | Inputs PIT for simulated decision/fill | Block above 35 bps or missing | Full acceptance test period | Quote provider or approved model | Current-spread leakage and threshold tests | BLOCKING |
| D23 | Event quality | Unexplained raw daily move | Daily | Prior raw close plus actions | abs raw return >20% unless action explained | By decision | Quarantine/block | Full period | Derived | Split/event explanation tests | REQUIRED |
| D24 | Targets | Signal/target/abstention record | Decision | All upstream inputs | Store versions, scores, reasons, weights, expiry | At emission | No target on lineage mismatch | Every decision | Derived | Determinism and hash-lineage tests | REQUIRED |
| D25 | Portfolio marks | Daily mark-to-market and completed-position P&L | Daily/event | Position lifetime | Raw tradable marks plus distributions/costs | Known at simulated mark time | Invalidate affected result | Full period | Derived | Cash-flow and reconciliation tests | REQUIRED |
| D26 | Short liabilities | Cash dividends and distributions owed | Event | Position lifetime | Apply signed liability on correct date | Known/effective under event data | Invalidate short attribution | Full period | Corporate-action source | Ex-date and liability tests | REQUIRED |
| D27 | Borrow | Availability/fee observations or conservative model | Daily/event | Position lifetime | Separate observed vs modeled states | PIT when observed; model frozen pretest | Never assume free/available | Full short test period | Broker/lending source or Phase 03 model | Missing-borrow and 2x-cost tests | BLOCKING_FOR_SHORT_CONCLUSION |
| D28 | Benchmarks | SPY total return and eligible-universe baselines | Daily/monthly | Full period | Phase 01 baseline formulas | PIT inputs only | Baseline unavailable/invalid | Full period | Derived/reference | Universe alignment and dividend tests | REQUIRED |

## Provider-proof-of-concept minimum sample

The trial must contain representative cases for:

- five delisted securities;
- five symbol or identity changes;
- five split/reverse-split cases;
- five cash-dividend cases;
- at least one merger or spinoff;
- at least one ticker-reuse case;
- two early-close sessions;
- earnings schedule revisions including BMO, AMC, and unknown time;
- complete and incomplete 10:00–10:30 intraday windows;
- a market-cap history check against dated source evidence;
- a sector-history change or explicit proof that the chosen source is effective-dated.

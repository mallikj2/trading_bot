# Phase 02 — Historical Short-Borrow Availability and Borrow-Cost Modeling

**Status:** IMPLEMENTATION PASS / SOURCE AND LIVE-BROKER GATES BLOCKED  
**Date:** 2026-08-06  
**Strategy:** `CSMOM-LS-v0.2`

## 1. Objective

Implement the Phase 02 short-borrow data and cost layer required by the approved Phase 01 long-short strategy without treating missing historical borrow evidence as free or available.

This task separates:

1. historical market-composite borrow evidence for research;
2. broker-specific current borrow evidence for executable paper/live shorts;
3. borrow-fee accrual;
4. recall, buy-in, withdrawal, and broker-restriction handling;
5. licensing and retention approval for any historical securities-lending source.

This task does **not** authorize live shorting and does **not** claim that a licensed historical borrow dataset has been acquired.

## 2. Binding Phase 01 requirements

The approved Phase 01 strategy requires:

- symbol-level borrow availability;
- borrow fee or conservative fee estimate;
- locate/confirmation behavior where applicable;
- recall, buy-in, dividend-liability, and reconciliation handling;
- daily exit evaluation for borrow invalidation;
- no assumption that missing historical borrow observations are free and available;
- 2x borrow costs in the pessimistic-cost test;
- live shorts prohibited until account, margin, broker, and borrow gates pass.

## 3. Engineering decisions

### 3.1 Point-in-time borrow observation

A `BorrowObservation` records:

- stable instrument ID;
- broker/provider/environment;
- observed, available, and expiry timestamps;
- available / unavailable / unknown state;
- easy / hard / unknown difficulty;
- annual borrow-fee rate when known;
- available-share quantity when known;
- source kind: broker-specific, market composite, or regulatory proxy;
- locate/confirmation identifier where applicable;
- immutable source snapshot and revision.

The observation is usable only when:

`available_at <= decision_at < expires_at`

Future revisions cannot change earlier short decisions.

### 3.2 Missing data fails closed

No historical row does not mean “easy to borrow.”

The research engine requires an explicit borrow observation for the decision instant. A separate coverage contract exists so sparse/event-only datasets cannot silently turn absence into availability or unavailability.

### 3.3 Historical versus live evidence

A market-composite securities-lending source may support historical research if its license, retention rights, timestamp semantics, coverage, and identity mapping are approved.

Market-composite evidence can **never** authorize a live short. Executable shorts require a broker-specific current observation and the later Schwab account/broker gate.

### 3.4 Entry and daily continuation

New short entry is rejected when any of the following applies:

- no valid point-in-time observation;
- provider is not approved;
- availability is unknown or unavailable;
- fee rate is missing;
- required quantity is missing or insufficient;
- hard-to-borrow is blocked by configured policy;
- rate exceeds an explicitly configured economic ceiling;
- a known recall, buy-in, withdrawal, or broker restriction is active;
- broker-specific evidence is required but only market-composite evidence exists.

The same checks run daily for existing shorts. Failure requires exit at the next execution window permitted by the strategy and market state.

### 3.5 Availability withdrawal proxy

When an approved historical source explicitly transitions from `AVAILABLE` to `UNAVAILABLE`, the engine derives an `AVAILABILITY_WITHDRAWN` event.

This is a conservative historical operational proxy. It is **not** mislabeled as an observed broker recall.

### 3.6 Borrow-fee accrual

The implemented fee formula follows Schwab's current published stock-borrow formula:

`fee = end_of_day_short_market_value × annual_quoted_rate / 360 × calendar_days`

The caller must explicitly supply the number of calendar accrual days and the applicable historical rate. The module does not invent an unverified settlement/accrual-start convention.

The Phase 01 pessimistic test applies a 2x multiplier to borrow costs.

Dividend/distribution liabilities remain in the corporate-action module rather than being double-counted here.

## 4. Historical source evaluation

### S&P Global Securities Finance

Technical fit: **strongest identified**.

Public product material states that the dataset includes long point-in-time history and daily securities-finance supply, demand, fees, availability, and recall-risk information suitable for backtesting borrow cost and availability.

Status: `TECHNICALLY_SUITABLE / COMMERCIAL_AND_RETENTION_TERMS_OPEN`.

### DataLend / EquiLend

Technical fit: **strong institutional candidate**.

Public material describes current and historical securities-lending fees, utilization, on-loan and inventory balances, transaction-level data, and related lending information.

Status: `TECHNICALLY_SUITABLE / COMMERCIAL_AND_RETENTION_TERMS_OPEN`.

### ORTEX

Technical fit: **strong retail-accessible API candidate**.

Public API documentation exposes historical cost-to-borrow and short-availability endpoints, historical ticker resolution, and daily borrowing data. Current API pricing lists a USD 49/month Trader plan and a USD 149/month Quant plan.

However, ORTEX's standard consumer terms prohibit creating a persistent independent database, restrict caching/storage to permitted use, and require deletion of API/Data Service data after termination. That conflicts with this project's immutable raw-snapshot and long-term reproducibility requirement.

Status: `TECHNICALLY_SUITABLE / STANDARD_CONSUMER_RETENTION_TERMS_INCOMPATIBLE`.

A guarded ORTEX adapter is included for schema evaluation only. Non-demo use requires an explicit `ORTEX_RESEARCH_LICENSE_APPROVED` governance flag.

### Interactive Brokers

IBKR publicly exposes current quantity, lender count, indicative borrow rate, and historical indicative borrow rates in its Short Securities Availability tools.

Status: `BROKER_SPECIFIC_REFERENCE / NOT_APPROVED_AS_CANONICAL_RESEARCH_SOURCE`.

It is not the approved live broker and its broker-specific historical rate is not automatically representative of Schwab execution economics.

### Public regulatory / clearing proxies

SEC Regulation SHO, threshold/fail data, FINRA short-interest/short-sale data, and OCC stock-loan volume are useful stress or crowding indicators but do not establish broker-specific borrow availability or quoted stock-borrow fees.

Status: `SUPPLEMENTARY_ONLY`.

## 5. Live Schwab boundary

Schwab's current pricing guide confirms that certain short positions may incur a stock-borrow fee calculated from end-of-day short market value and a quoted interest rate divided by 360, with the rate subject to daily change.

The live system still requires credentialed contract tests for:

- account margin status;
- short permission;
- broker-provided symbol shortability;
- hard-to-borrow state;
- current quantity and rate fields if exposed;
- locate/confirmation workflow;
- recall / buy-in handling;
- reconciliation behavior.

No public-document inference is allowed to authorize live short orders.

## 6. Implemented artifacts

- `src/trading_bot/data/borrow.py`
- `src/trading_bot/data/adapters/ortex_borrow.py`
- `configs/data/historical_short_borrow.yaml`
- focused unit tests and integration tests;
- adversarial fixture set;
- source-evaluation and trial-runbook documentation.

## 7. Validation

The focused suite validates:

- future borrow revision exclusion;
- observation expiry;
- conflicting same-revision rejection;
- regulatory-proxy inability to assert availability;
- missing fee rejection;
- quantity insufficiency rejection;
- explicit hard-to-borrow policy;
- broker-specific live requirement;
- recall and future-recall semantics;
- explicit economic-rate ceiling;
- Schwab-style 360-day fee formula;
- Phase 01 2x pessimistic borrow multiplier;
- dense coverage semantics;
- daily continuation failure on expired borrow;
- derived availability-withdrawal events;
- ORTEX research-license gating and historical ticker-resolution request construction.

## 8. Gate assessment

### Engineering implementation

**PASS**

The provider-independent borrow state, point-in-time selector, availability gate, daily continuation gate, event model, and borrow-cost accrual model are implemented and tested.

### Historical source evidence

**BLOCKED / OPEN**

Before historical short borrow is accepted for the final backtest, the project still requires:

1. a provider contract allowing non-display quantitative research;
2. long-term immutable raw-data retention sufficient for reproducibility;
3. credentialed representative historical samples;
4. identity, delisting, and ticker-reuse verification;
5. daily point-in-time availability and fee coverage report;
6. known interpretation of missing rows;
7. recall/withdrawal coverage or a preregistered conservative proxy policy;
8. frozen source version and manifest hashes.

### Live Schwab gate

**BLOCKED**

Live shorting remains prohibited pending credentialed broker/account validation.

### Phase 02 overall

**ACTIVE**

Other unresolved gates from earlier Phase 02 tasks remain open, including core-provider licensing/trial evidence, earnings-source licensing/sample, spread calibration source, and complex corporate-action provider reconciliation.

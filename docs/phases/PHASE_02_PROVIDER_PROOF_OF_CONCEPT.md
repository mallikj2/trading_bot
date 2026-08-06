# Phase 02 — Research Provider Proof of Concept

> **Task:** Phase 02 Task 2 — provider proof of concept  
> **Version:** 0.1  
> **Date:** 2026-08-05  
> **Status:** CONDITIONAL PASS — contract and harness complete; credentialed data trial pending  
> **Strategy:** `CSMOM-LS-v0.2`  
> **Live authorization:** None

## 1. Objective

Select and validate a practical data-provider architecture for the approved Phase 01 strategy without exceeding the initial USD 80 monthly recurring data budget or weakening any point-in-time requirement.

This task distinguishes three evidence levels:

1. `DOCUMENTED` — supported by current official provider documentation.
2. `HARNESS_VALIDATED` — local schemas, validators, and adversarial fixtures pass.
3. `CREDENTIALED_VALIDATED` — actual provider responses pass the same validators.

Only the first two levels are complete. No licensed-data coverage result is fabricated.

## 2. Governing requirements

The provider stack must support or enable:

- NYSE/Nasdaq common-stock universe reconstruction by historical date;
- inactive and delisted securities;
- stable identity independent of ticker;
- raw daily OHLCV and corporate actions;
- at least ten years of history for the final acceptance interval;
- five-minute or finer data for the next-session 10:00–10:30 ET VWAP benchmark;
- point-in-time market capitalization;
- point-in-time sector classification;
- earnings schedules with historical revisions and known-at timestamps;
- an observed or preregistered modeled spread;
- immutable snapshots, manifests, and reproducible rebuilds.

## 3. Provider decision

### 3.1 Primary credentialed trial candidate — Massive Stocks Developer

**Decision:** Use Massive Stocks Developer as the first credentialed provider trial.

Documented fit:

- USD 79/month individual plan;
- ten years of historical stock data;
- all US stock tickers;
- minute aggregates and downloadable flat files;
- daily aggregates, reference data, and corporate actions;
- point-in-time ticker queries by date;
- active/inactive status, delisting date, exchange, CIK, Composite FIGI, Share Class FIGI, and security type;
- raw or split-adjusted aggregate requests;
- historical splits and dividends.

This is the only evaluated single-provider plan that documents both the ten-year price horizon and intraday aggregates while remaining within the approved USD 80 monthly recurring ceiling.

Documented limitations:

- historical quotes are not included in the Developer plan;
- ticker-events support is experimental and the endpoint documentation currently guarantees ticker changes, not a complete merger/spinoff identity graph;
- reference market capitalization and classification fields are not accepted as point-in-time fundamentals without a separate validation;
- earnings schedule revisions are not supplied;
- historical short-borrow data is not supplied.

### 3.2 Free companion source — SEC EDGAR

SEC EDGAR is selected as the source for a low-cost point-in-time enrichment proof of concept:

- filing submission history;
- acceptance timestamps;
- XBRL facts;
- filing-level assigned SIC classification;
- filing-level common-shares facts where unambiguous.

Proposed market-cap calculation:

```text
issuer_market_cap_pit = sum(class_raw_close × class_shares_outstanding_pit)
```

For a single-class issuer:

```text
market_cap_pit = raw_close × latest_unambiguous_shares_fact_known_at_freeze
```

The record is rejected when share-class mapping is ambiguous, a filing acceptance timestamp is unavailable, or the shares fact cannot be tied to the security/issuer without double counting.

Proposed sector taxonomy:

```text
SEC_SIC_DIVISION_V1
```

The latest filing-header SIC accepted by the decision timestamp is mapped to a frozen broad SIC division. This is a provisional Phase 02 taxonomy, not a claim that SIC is economically superior to GICS.

### 3.3 Earnings revisions — unresolved hard blocker

Wall Street Horizon documents a dedicated time-stamped earnings-date revision product, DateBreaks. Public pricing was not verified. A quote and historical-sample trial are required.

Current low-cost calendar APIs that publish historical or upcoming earnings dates do not, based on the reviewed official documentation, establish a complete historical sequence of what date/time was known at every prior decision timestamp.

Therefore:

- current calendars must not be backfilled;
- actual earnings dates alone do not satisfy the approved entry-blocking rule;
- Phase 03 final acceptance remains blocked until either:
  1. a revision-aware historical feed passes the trial; or
  2. a separately approved Phase 01 strategy amendment changes the event rule.

### 3.4 Backup/cross-validation candidate — Norgate Data Platinum

Norgate Platinum remains a useful cross-validation or backup candidate for:

- survivorship-aware daily prices;
- delisted securities;
- historical major-exchange-listing indicators;
- original unadjusted close and volume;
- dividends and capital-event indicators.

It is not selected as the primary stack because:

- it does not provide intraday data;
- fundamentals are current rather than historical point-in-time;
- access uses a proprietary local Windows database and lapses when the subscription expires;
- combining it with a ten-year intraday source exceeds the initial recurring budget.

## 4. Capability verdict

| Contract | Primary proposed source | Documentation verdict | Credentialed verdict |
|---|---|---:|---:|
| PIT ticker universe | Massive | PASS-DOC | PENDING |
| Common-stock type and exchange | Massive | PASS-DOC | PENDING |
| Delisted/inactive symbols | Massive | PASS-DOC | PENDING |
| Stable identity | Massive FIGI/CIK + local instrument master | PARTIAL-DOC | PENDING |
| Raw daily OHLCV | Massive | PASS-DOC | PENDING |
| Splits/dividends | Massive | PASS-DOC | PENDING |
| Merger/spinoff identity | Massive + SEC filings + manual exception queue | PARTIAL-DOC | PENDING |
| Ten-year minute aggregates | Massive Developer | PASS-DOC | PENDING |
| 10:00–10:30 VWAP | Derived from Massive minute bars | PASS-DESIGN | PENDING |
| PIT shares/market cap | SEC filings + raw prices | PASS-DESIGN | PENDING |
| PIT sector | SEC filing-header SIC | PASS-DESIGN | PENDING |
| Earnings schedule revisions | WSH DateBreaks candidate | PASS-DOC | PENDING/UNPRICED |
| Historical spread | Preregistered proxy | PASS-DESIGN | CALIBRATION PENDING |
| Historical borrow | Conservative Phase 03 model | DEFERRED | DEFERRED |

## 5. Trial sample

The credentialed run must include at minimum:

### Delisted/inactive candidate cases

- `TWTR`
- `ATVI`
- `CERN`
- `WORK`
- `XLNX`

### Symbol/identity candidate cases

- `FB` → `META`
- `SQ` → `XYZ`
- `ANTM` → `ELV`
- `VIAC` → `PARA`
- `DWAC` → `DJT`

### Corporate-action candidate cases

- AAPL 4-for-1 split in 2020
- TSLA 5-for-1 split in 2020 and 3-for-1 split in 2022
- NVDA 4-for-1 split in 2021 and 10-for-1 split in 2024
- AMZN 20-for-1 split in 2022
- GE reverse split in 2021
- GEHC spinoff from GE in 2023
- ordinary cash dividends for AAPL, MSFT, XOM, JPM, and KO

### Calendar and execution cases

- at least two official early-close sessions;
- one complete 10:00–10:30 ET window;
- one missing-bar window;
- one zero-volume or halted window;
- one DST-boundary week;
- one symbol with a split near the VWAP sample date.

### Earnings cases

The WSH or alternative sample must demonstrate:

- BMO, AMC, during-session, and unknown timing;
- tentative to confirmed change;
- date revision;
- cancellation;
- a late revision after a position decision;
- explicit `known_at` or message timestamp.

## 6. Credentialed pass criteria

The provider trial passes only when all applicable checks succeed:

1. Historical ticker queries return inactive securities on dates when they were active.
2. Common stock, exchange, CIK, and FIGI fields are stable and noncontradictory.
3. The five delisted cases contain valid bars before delisting and none after terminal trading.
4. The five symbol-change cases do not merge unrelated issuers.
5. Raw daily and minute bars satisfy OHLCV invariants.
6. Split-adjusted and raw requests reconcile to split events.
7. All six expected five-minute intervals in the execution window are present for a valid fill.
8. An incomplete or zero-volume window produces no fill.
9. SEC shares facts selected for a historical freeze exclude later filings and restatements.
10. Multi-class or ambiguous share facts fail closed.
11. SIC history uses only filings accepted by the decision timestamp.
12. Earnings revisions preserve every known-at version.
13. Raw downloads and normalized outputs have immutable hashes.
14. Provider license terms permit the intended personal local research and retention model.

## 7. Current task result

### CONDITIONAL PASS

Completed:

- current official documentation comparison;
- provider shortlist and budget screen;
- primary trial selection;
- exact credentialed trial plan;
- schema and validator implementation;
- adversarial local fixture tests;
- provisional SEC market-cap and SIC methods;
- failure and escalation policy.

Not completed:

- no Massive API key was available;
- no licensed Norgate trial was installed;
- no Wall Street Horizon sample was available;
- no provider coverage result is claimed;
- spread proxy is not calibrated against observed consolidated quotes.

## 8. Next action

Run the credentialed Massive trial with the supplied CLI, then attach its raw JSON/CSV snapshots and generated report to the repository. In parallel, request a Wall Street Horizon DateBreaks historical sample and quote.

Phase 03 final acceptance remains prohibited until the credentialed trial passes and the earnings-revision blocker is resolved.

## 9. Official sources reviewed

Retrieved 2026-08-05:

1. Massive stocks plans and coverage: https://massive.com/stocks
2. Massive all-tickers point-in-time endpoint: https://massive.com/docs/rest/stocks/tickers/all-tickers
3. Massive aggregate bars: https://massive.com/docs/rest/stocks/aggregates/custom-bars
4. Massive minute flat files: https://massive.com/docs/flat-files/stocks/minute-aggregates
5. Massive splits: https://massive.com/docs/rest/stocks/corporate-actions/splits
6. Massive dividends: https://massive.com/docs/rest/stocks/corporate-actions/dividends
7. Massive ticker events: https://massive.com/docs/rest/stocks/corporate-actions/ticker-events
8. SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
9. SEC webmaster/fair-access guidance: https://www.sec.gov/about/webmaster-frequently-asked-questions
10. Wall Street Horizon earnings calendar and DateBreaks: https://www.wallstreethorizon.com/earnings-calendar
11. Norgate stock packages: https://norgatedata.com/stockmarketpackages.php
12. Norgate data content: https://norgatedata.com/data-content-tables.php
13. Norgate overview/access model: https://norgatedata.com/index.php/pricing/

# Provider PoC — Credentialed Results

> **Status:** NOT RUN  
> **Provider plan:** `<record exact plan>`  
> **Retrieval window:** `<UTC start>` to `<UTC end>`  
> **Adapter version:** `<git commit or version>`  
> **Schema version:** `1`

## 1. Executive verdict

- Overall result: `PASS | CONDITIONAL PASS | FAIL`
- Data contracts passed: `<count>`
- Data contracts failed: `<count>`
- Blocking discrepancies: `<list>`
- License-retention review: `PASS | FAIL | PENDING`

No section may be marked passed without linked raw-snapshot hashes.

## 2. Environment

| Item | Value |
|---|---|
| OS | |
| Python | |
| Repository commit | |
| Massive plan | |
| SEC user-agent identifier | Redact contact from published report if needed |
| Timezone database version | |

## 3. Raw snapshot register

| Snapshot ID | Provider | Request/coverage | Retrieved at UTC | Record count | SHA-256 | Result |
|---|---|---|---|---:|---|---|
| | | | | | | |

## 4. Contract results

| Contract | Test cases | Evidence files | Result | Discrepancies |
|---|---|---|---|---|
| PIT ticker universe | | | NOT RUN | |
| Delisted/inactive history | | | NOT RUN | |
| Stable identity and symbol changes | | | NOT RUN | |
| Raw daily OHLCV | | | NOT RUN | |
| Splits and dividends | | | NOT RUN | |
| Merger/spinoff identity | | | NOT RUN | |
| Ten-year minute aggregates | | | NOT RUN | |
| 10:00–10:30 ET VWAP | | | NOT RUN | |
| PIT shares/market cap | | | NOT RUN | |
| PIT SIC sector | | | NOT RUN | |
| Earnings known-at revisions | | | NOT RUN | |
| Historical spread calibration | | | NOT RUN | |

## 5. Adversarial cases

Record the exact historical date chosen for each provider query rather than assuming today’s symbol resolves historically.

### Delisted/inactive

| Instrument | Last active-session evidence | Post-terminal evidence | Identity continuity | Result |
|---|---|---|---|---|
| TWTR | | | | NOT RUN |
| ATVI | | | | NOT RUN |
| CERN | | | | NOT RUN |
| WORK | | | | NOT RUN |
| XLNX | | | | NOT RUN |

### Symbol changes

| Old symbol | New symbol | Provider event | Stable local instrument ID | Result |
|---|---|---|---|---|
| FB | META | | | NOT RUN |
| SQ | XYZ | | | NOT RUN |
| ANTM | ELV | | | NOT RUN |
| VIAC | PARA | | | NOT RUN |
| DWAC | DJT | | | NOT RUN |

### Corporate actions and VWAP

| Case | Raw/adjusted reconciliation | Intraday completeness | Result |
|---|---|---|---|
| AAPL split | | | NOT RUN |
| TSLA splits | | | NOT RUN |
| NVDA splits | | | NOT RUN |
| AMZN split | | | NOT RUN |
| GE reverse split | | | NOT RUN |
| GEHC spinoff | | | NOT RUN |

## 6. Point-in-time SEC enrichment

For each selected shares or SIC observation record:

- accession number;
- filing form;
- reporting period;
- filed/accepted timestamp used;
- point-in-time availability timestamp;
- XBRL concept and unit;
- security-class mapping;
- rejection reason for ambiguous cases.

## 7. Earnings-revision sample

The sample passes only when it preserves at least two actual versions for the same event and includes a known-at timestamp for every version. A current-only calendar fails.

## 8. License review

Record the exact terms governing:

- personal/nonprofessional use;
- local raw-data retention;
- derived-data retention after cancellation;
- redistribution prohibition;
- use in backtests and local automated trading;
- audit/log retention.

## 9. Final gate

- Credentialed provider PoC: `PASS | CONDITIONAL PASS | FAIL`
- Earnings revision blocker: `RESOLVED | OPEN`
- Spread calibration blocker: `RESOLVED | OPEN`
- Phase 02 gate recommendation: `PASS | CONDITIONAL PASS | FAIL`

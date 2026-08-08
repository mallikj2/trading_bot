# Phase 02 — Core Research Provider Selection and Trial

**Date:** 2026-08-08  
**Task status:** LICENSE DECISION PASS / CREDENTIALED TRIAL BLOCKED  
**Phase 02 status:** ACTIVE

## Objective

Resolve the core-provider retention problem created by the rejection of Massive's public individual terms, select a legally retainable private research archive, and make the remaining credentialed evidence explicit and executable.

## Decision

### Core EOD archive: Kibot

Kibot is selected for the first paid core-price trial because its public license is compatible with private local retention and its EOD plan is inexpensive. Research ingestion must use unadjusted data and immutable snapshots.

### PIT security master and exact execution data: separate companion

Kibot is deliberately **not** selected as the historical identity authority. Provider documentation says symbol files are rewritten after ticker changes and reused tickers can contain unrelated issuer histories. That conflicts with the platform's immutable instrument-identity contract.

Databento is the preferred companion candidate because its security master and symbology documentation explicitly support point-in-time identifiers, listing/delisting information, and historical symbol preservation. Its historical trades can also support exact execution-window VWAP. This companion remains approval-gated.

## Code delivered

- `KibotClient` with login/session transport and explicit paid-license acknowledgement gate;
- unadjusted daily-history retrieval;
- daily, minute, and tick parsers;
- exact size-weighted trade VWAP helper;
- adjustments parser that preserves raw descriptions instead of over-interpreting unvalidated ratios;
- immutable text/CSV snapshot persistence;
- credential secret redaction including username/password;
- core-provider trial environment/blocked-result runner;
- approval-gated Databento PIT security-master and historical-trades companion adapter with an explicit configured dataset (never guessed).

## Point-in-time safety decisions

1. Kibot back-adjusted history is never canonical raw data.
2. Kibot ticker is never a stable identity key.
3. Current active/delisted lists are never treated as historical constituent snapshots.
4. Historical files containing ticker reuse must be split only from independent listing/identity evidence.
5. Daily Kibot data is conservatively unavailable until the documented next update window; it is not assumed available at close+30 minutes.
6. Final acceptance VWAP cannot be approximated from minute OHLC bars.

## Trial result in this environment

No paid Kibot credentials, Databento API key, or project SEC monitored-contact User-Agent were available. Network access from the validation container is also unavailable. The runner therefore correctly returns `BLOCKED`; no credentialed provider claim is made.

## Gate changes

- P02-G05: **PASS** — Kibot private research retention license approved within personal scope.
- P02-G04: **BLOCKED** — paid representative core-price trial not run.
- P02-G18: **BLOCKED** — PIT security-master and exact-execution companion license/trial not run.

Phase 03 remains prohibited.

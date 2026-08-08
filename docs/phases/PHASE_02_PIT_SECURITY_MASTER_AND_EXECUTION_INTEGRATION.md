# Phase 02 — PIT Security Master and Exact-Execution Integration

**Date:** 2026-08-08  
**Task status:** ENGINEERING PASS / CREDENTIALED EVIDENCE BLOCKED  
**Phase 02 status:** ACTIVE

## Objective

Close the internal integration gap between the approved Phase 01 universe/execution rules and the remaining external P02-G04/P02-G18 evidence gates.

The task has four deliverables:

1. normalize a point-in-time security master without allowing effective dates to leak before provider record timestamps;
2. use stable historical identity rather than ticker to query execution evidence;
3. compute the frozen next-session 10:00–10:30 ET execution VWAP from trade-level records; and
4. generate the sector-blind monthly target ledger required by P02-G07.

No paid-provider coverage or license result is claimed by this task.

## Architecture decision

### Kibot remains the retained EOD archive

Kibot remains the selected retained unadjusted daily-price archive under the already-approved private-use retention decision. It remains prohibited as the historical identity authority.

### Databento remains the preferred PIT/execution companion candidate

Databento is the preferred candidate because its security master is explicitly point-in-time, maintains listing/security/issuer identifiers, tracks listed and delisted securities, and documents history beginning in 2005. Its trade schema exposes trade-level price, size, timestamps, instrument ID, and quality flags.

This is still a **candidate**, not an approved production source. Actual account terms, retention/reproducibility rights, the selected historical execution dataset, and the execution-coverage profile must pass a credentialed trial.

## Point-in-time knowledge rule

Provider timestamps have different meanings:

- `ts_effective`: when the record's economic/reference details are effective;
- `ts_record`: when that record version last changed in the provider PIT stream.

For any historical decision time `T`, a security-master record is usable only when:

```text
record.ts_effective <= T
AND
record.ts_record <= T
```

A record that is effective in the past but was recorded later cannot be backfilled into the earlier decision.

## Stable identity rule

Ticker is never the permanent execution or universe identity.

The adapter normalizes provider `security_id` into an immutable internal UUID and retains:

- `listing_id`;
- `security_id`;
- `issuer_id`;
- FIGI;
- US code/CUSIP-equivalent field where supplied;
- CIK;
- symbol aliases;
- primary exchange;
- listing status;
- security type;
- listing/delisting dates.

Final historical trade requests prefer stable symbology in this order:

1. FIGI;
2. US code;
3. ISIN;
4. ticker only when no approved stable identifier exists and the case is separately reviewed.

## Sector-blind target ledger

P02-G07 must measure sector coverage against names that would otherwise satisfy the Phase 01 monthly universe rules. It may not remove a name simply because sector data is missing.

`build_sector_blind_target_ledger()` therefore runs the same frozen universe policy while removing only the sector requirement. Each otherwise-eligible row must then be independently confirmed by the PIT security master as:

- a common stock;
- on NYSE or Nasdaq;
- listed at the monthly freeze;
- mapped to an immutable provider security;
- mapped to a CIK known at that freeze.

Missing CIK, ambiguous primary listing, security-type conflict, or exchange conflict is an upstream evidence failure. It is never converted to a convenient sector exclusion.

The generated ledger is directly consumable by the SEC sector coverage crawler.

## PIT market-cap corroboration

The security master can also carry `shares_outstanding` plus an effective shares date. A helper now supports:

```text
PIT market cap = raw close × PIT shares outstanding
```

subject to both inputs being known by the decision time and the shares effective date not being in the future.

This is an **alternate/corroborating path** only. It does not silently replace the existing SEC filing-based shares pipeline until a credentialed reconciliation is completed.

## Exact execution benchmark

The Phase 01 benchmark remains:

```text
next regular session, 10:00:00 ET <= trade time < 10:30:00 ET
```

The execution engine:

- converts the New York window to UTC using the historical timezone rules;
- consumes trade-level records, not OHLC bars;
- requires a single provider instrument identity in each window;
- rejects non-positive prices or sizes;
- rejects records carrying configured bad timestamp/book-quality flags;
- computes size-weighted VWAP:

```text
VWAP = sum(price * size) / sum(size)
```

## Execution-coverage boundary

A trade schema is exact **within the selected dataset**, but that does not automatically make the dataset a complete market-wide tape.

Therefore the code requires a separate governance flag:

```text
DATABENTO_EXECUTION_COVERAGE_APPROVED=true
```

before a credentialed execution trial can run.

The supporting evidence must document:

- component lit venues;
- off-exchange/TRF coverage;
- historical changes in that coverage;
- whether the resulting benchmark can legitimately be called the frozen Phase 01 market-wide execution VWAP.

A venue-only feed, or a derived composite whose coverage has not been accepted, cannot silently satisfy P02-G18.

## Credentialed trial boundary

The standalone trial runner requires all of:

```text
DATABENTO_API_KEY
DATABENTO_RESEARCH_LICENSE_APPROVED=true
DATABENTO_EXECUTION_DATASET=<approved dataset>
DATABENTO_EXECUTION_COVERAGE_APPROVED=true
```

Without these, it returns `BLOCKED` before making a provider request.

A final P02-G18 PASS additionally requires the representative panel in `configs/data/pit_security_master_execution_acceptance.yaml` and account-specific retention/reproducibility rights.

## Offline validation completed

The test suite now covers:

- future `ts_record` exclusion;
- latest-known PIT record selection;
- ticker-reuse detection;
- exchange/security-type cross-checks;
- missing CIK fail-closed behavior;
- sector-blind universe denominator behavior;
- point-in-time market-cap derivation;
- EST and EDT execution-window conversion;
- trade-quality rejection;
- multiple-provider-instrument rejection;
- end-to-end PIT identity → SEC target-ledger → exact trade VWAP bridge.

## Gate status

- **P02-G04:** BLOCKED — paid composite core-stack representative trial has not been completed.
- **P02-G18:** BLOCKED — Databento/equivalent account license, execution coverage profile, and representative PIT/trade trial have not been approved.
- **P02-G07:** BLOCKED — the sector-ledger builder is now implemented, but the real target ledger still depends on the credentialed PIT/core stack plus the monitored-contact SEC crawl.

Phase 03 remains prohibited.

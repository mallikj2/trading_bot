# Phase 02 — Production Provider Adapter Architecture

**Version:** 0.2  
**Date:** 2026-08-05  
**Status:** Implemented locally; credentialed evidence pending

## 1. Boundary

Provider adapters are an external ingestion layer above the deterministic Phase 02 kernel.

```text
Provider HTTPS API
    |
    v
SafeJsonClient
  - HTTPS host pinning
  - declared User-Agent
  - rate limiting
  - bounded retries
  - pagination validation
    |
    v
Immutable raw snapshot
  - response.json
  - SHA-256 source hash
  - redacted request parameters
  - dataset manifest
    |
    v
Provider-specific schema validation
    |
    v
Kernel contracts
  - ticker reference / SymbolAlias
  - DailyBar / IntradayBar
  - CorporateAction
  - SharesOutstandingObservation
  - MarketCapObservation
  - SectorObservation only after PIT proof
```

Network retrieval never writes directly to normalized research tables. The raw response and manifest must exist first.

## 2. Massive adapter

Implemented read-only methods:

- dated active and inactive ticker snapshots;
- dated ticker overview;
- custom daily and minute aggregates with `adjusted=false`;
- splits;
- dividends;
- ticker-change events;
- pagination through provider-owned `next_url` values restricted to `api.massive.com`.

Normalization behavior:

- daily-bar observation time comes from the versioned exchange calendar, not from an assumed midnight timestamp;
- daily availability defaults to official close plus 30 minutes;
- intraday availability is interval end plus a configured lag;
- six valid five-minute intervals are required for the Phase 01 10:00–10:30 ET benchmark;
- split and dividend event availability defaults conservatively to the effective/ex-date session open;
- ticker-event history becomes half-open ticker-alias intervals;
- direct historical market-cap and SIC output is blocked until the credentialed as-of trial passes.

The ticker-events endpoint is documented by Massive as experimental. The adapter therefore fails on unsupported event types and preserves the raw payload for later reprocessing.

## 3. SEC adapter

Implemented read-only methods:

- submissions JSON;
- older submissions fragments;
- company-facts JSON.

The adapter requires a declared `SEC_USER_AGENT` containing a monitored contact email and enforces a configured request rate no higher than the SEC's 10-request-per-second fair-access ceiling.

Point-in-time shares pipeline:

1. Convert submissions parallel arrays into filing rows.
2. Build `accession_number -> acceptance_datetime` mappings.
3. Read `dei:EntityCommonStockSharesOutstanding` and `us-gaap:CommonStockSharesOutstanding` facts.
4. Reject facts that cannot be joined to an acceptance timestamp.
5. Add a one-minute conservative API-processing buffer.
6. Reject conflicting values for the same accession and period.
7. Select the latest reporting period whose fact was available at the decision timestamp.
8. Derive market cap as `raw close × point-in-time shares outstanding`.

Filing date alone is never used as an availability timestamp.

## 4. Historical-sector correction

The SEC submissions API exposes a top-level SIC value, but the API contract does not provide an effective-dated SIC history per filing. The production adapter therefore represents this field as `CurrentSicReference` and prohibits promotion to `SectorObservation`.

A historical sector may be emitted from Massive ticker overview only after a credentialed dated-query test demonstrates that SIC is truly returned as of the requested historical date. Until then, Phase 02's historical-sector gate remains blocking.

## 5. Failure behavior

| Failure | Behavior |
|---|---|
| Missing Massive key | Credentialed Massive checks blocked |
| Missing compliant SEC User-Agent | SEC network checks blocked |
| Pagination leaves approved host | Abort ingestion |
| 429/5xx response | Bounded exponential retry |
| Invalid provider status/schema | Quarantine snapshot; no normalization |
| Raw target path exists | Reject overwrite |
| Secret in request parameters | Redact from manifest |
| Historical ticker semantics unvalidated | Block normalization |
| Direct historical market cap unvalidated | Block field |
| Historical SIC semantics unvalidated | Block sector |
| SEC fact lacks acceptance timestamp | Reject fact |
| Conflicting share-class values | Block market cap |
| Incomplete or zero-volume VWAP window | No fill |

## 6. Out of scope

- order execution;
- streaming WebSocket ingestion;
- historical earnings revisions;
- spread-model calibration;
- borrow availability;
- merger and spinoff economic normalization;
- provider license approval itself.

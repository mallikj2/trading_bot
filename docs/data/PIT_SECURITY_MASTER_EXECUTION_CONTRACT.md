# Point-in-Time Security Master and Exact-Execution Contract

**Version:** 0.2.0  
**Status:** Approved engineering contract; external source acceptance pending

## Security-master record contract

A normalized record must preserve at least:

| Field | Requirement |
|---|---|
| internal `instrument_id` | immutable; derived from provider security identity, never ticker |
| provider `listing_id` | required |
| provider `security_id` | required |
| provider `issuer_id` | retained |
| symbol aliases | retained, not identity |
| FIGI / stable code | retained when supplied |
| CIK | required for otherwise-eligible US common stocks before sector crawl |
| primary exchange | point-in-time |
| security type | point-in-time |
| listing status | point-in-time |
| listing/delisting date | retained when supplied |
| `ts_effective` | economic/reference effective time |
| `ts_record` | provider knowledge/change time |
| shares outstanding/date | retained when supplied |
| source snapshot | immutable lineage |

## As-of selector

For decision time `T`, eligible records satisfy both:

```text
ts_effective <= T
ts_record <= T
```

The selected row is the latest unambiguous primary-listing record known at `T`.

The selector must fail on:

- no eligible PIT row;
- conflicting latest rows;
- ambiguous primary listings;
- unknown security type or exchange where the universe requires them.

## Ticker reuse

A symbol observed against more than one provider `security_id` is a ticker-reuse condition. Historical files must not concatenate or merge those securities merely because the display symbol matches.

## Sector-blind ledger contract

The P02-G07 denominator applies every Phase 01 universe criterion except sector.

For each eligible row, PIT identity must independently confirm:

```text
security_type == COMMON_STOCK
exchange in {NYSE, NASDAQ}
listing_state == LISTED
CIK is known by freeze timestamp
```

Any otherwise-eligible name lacking those confirmations blocks ledger generation; it may not be dropped to improve sector coverage.

## Market-cap corroboration

When provider shares outstanding are used:

```text
market_cap = raw_close * shares_outstanding
```

Requirements:

- raw close was available by `decision_at`;
- security-master record was available by `decision_at`;
- shares effective date is not after `decision_at.date()`;
- shares value is positive;
- instrument identities match.

This path remains corroborating until reconciled against the approved filing-based path.

## Exact execution contract

Window:

```text
10:00:00 America/New_York <= ts_event < 10:30:00 America/New_York
```

The window is converted to UTC per session date; fixed UTC offsets are prohibited.

Trade requirements:

- positive price;
- positive size;
- one provider instrument identity;
- no rejected quality flags;
- stable historical symbology used for the request where available.

VWAP:

```text
sum(price_i * size_i) / sum(size_i)
```

No minute OHLC approximation is accepted for final Phase 03 execution evidence.

## Coverage-profile contract

The selected dataset must separately document the venue and off-exchange prints represented in its `trades` schema over the acceptance interval.

`DATABENTO_EXECUTION_COVERAGE_APPROVED=true` is a governance acknowledgement that the chosen source profile has been reviewed and is adequate for the frozen Phase 01 benchmark. It is not set automatically by code or by possession of an API key.

## Data lineage

Credentialed records must be persisted as immutable raw snapshots with:

- provider and dataset;
- request range and symbology;
- retrieval timestamp;
- source hashes;
- adapter version;
- row counts;
- coverage metadata;
- parent manifest IDs.

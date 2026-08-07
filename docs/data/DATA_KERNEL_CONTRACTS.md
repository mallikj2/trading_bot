# Phase 02 Minimum Data Kernel Contracts

## Time contract

All datetimes are timezone-aware and normalized to UTC. Exchange-local time is used only when creating versioned session records.

Historical eligibility is always:

```text
available_at <= decision_at
```

Feature availability is:

```text
max(input.available_at) + processing_latency
```

## Identity contract

- `instrument_id` is an immutable UUID.
- Ticker and exchange are effective-dated aliases.
- Symbol changes preserve the same instrument identity.
- Non-overlapping ticker reuse by a new issuer is allowed.
- Overlapping ownership of the same exchange/ticker pair is rejected.

## Daily-bar contract

Each bar stores raw OHLCV, session date, observed time, availability time, provider revision, source snapshot, and quality state.

Required invariants:

```text
open, high, low, close > 0
high >= max(open, close, low)
low <= min(open, close, high)
volume >= 0
provider_revision >= 0
```

Raw bars are not adjusted in place.

## Corporate-action contract

The kernel now requires revision-aware, point-in-time action processing. Every
build must have complete coverage evidence through the decision timestamp. An
empty action list without coverage is invalid.

Supported continuing actions are splits, reverse splits, cash dividends, stock
dividends, and spinoffs. Supported terminal actions are mergers, acquisitions,
delistings, liquidations, and bankruptcies. Noncash distributions and stock
consideration require explicit point-in-time valuations.

The data layer stores separately:

- raw tradable close;
- current-session price-eligibility close;
- split-adjusted close;
- total-return-adjusted close;
- forward total-return index.

The latest action or valuation revision satisfying `available_at <= decision_at`
is selected. Later corrections and cancellations create new versions and cannot
rewrite an earlier frozen build. Tender offers, rights distributions, ambiguous
same-session terminal events, missing ex-date bars, missing prior bars, missing
valuations, and currency mismatches fail closed.

See `CORPORATE_ACTION_TOTAL_RETURN_CONTRACT.md` for the full equations and
position-transformation rules.

## Dataset-manifest contract

Every research dataset manifest includes:

- provider and adapter version;
- schema and dataset version;
- retrieval time and coverage;
- exact request parameters;
- all raw source paths, byte sizes, and SHA-256 hashes;
- record count and license classification;
- parent manifests and quality report hash where applicable.

Reusing an immutable target path is an error, even when the bytes are identical.

## Monthly-universe contract

The builder implements the approved Phase 01 boundaries:

| Rule | Boundary |
|---|---:|
| Exchange | NYSE or Nasdaq |
| Security type | Common stock |
| Current-session price-eligibility close | At least USD 10 |
| Point-in-time market cap | At least USD 2 billion |
| Median ADV60 | At least USD 25 million |
| Valid history | At least 300 sessions |
| VOL20 annualized | No more than 80% |
| Sector | Required |
| Listing state | Listed |
| Quality | Valid |

Boundary values are inclusive. Every rejected instrument retains all applicable reason codes, not only the first failure.

## Reproducibility contract

Identical raw bytes, request parameters, versions, timestamps, normalized inputs, and policy versions must produce identical manifest and universe hashes. Changing any declared input must produce a different lineage hash.

## Revision-aware earnings schedules

The earnings calendar is implemented in `src/trading_bot/data/earnings.py` rather than extending the generic contract module with provider-specific semantics.

Required record types:

- `EarningsScheduleRevision`: immutable fiscal-event schedule version with `available_at`, timing, status, revision kind, and source lineage.
- `EarningsCoverageObservation`: explicit evidence that the calendar is complete through a forward date.

Historical selection uses only revisions available at the decision time. Missing coverage fails closed. See `EARNINGS_SCHEDULE_POINT_IN_TIME_CONTRACT.md` for full policy.

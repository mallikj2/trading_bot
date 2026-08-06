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

The kernel supports as-of split and reverse-split adjustment. A split affects a historical raw price only when:

```text
price_observed_at < action.effective_at <= decision_at
and action.available_at <= decision_at
```

For a split with `new_shares / old_shares = R`, the historical price factor is:

```text
old_shares / new_shares = 1 / R
```

When the same action has revisions, the latest revision known by the decision timestamp is selected.

Cash dividends, spinoffs, mergers, tender offers, and other actions are represented by the contract but require later total-return and lifecycle processors. They may not be silently ignored by provider adapters.

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
| Adjusted close | At least USD 10 |
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

# Point-in-Time Total-Return Algorithm

## Inputs

For one immutable `instrument_id` and one `decision_at`:

1. daily raw OHLCV revisions;
2. corporate-action revisions;
3. noncash valuation revisions;
4. complete corporate-action coverage evidence;
5. reporting currency and exchange timezone.

## Selection

1. Select the latest daily-bar revision per session available by `decision_at`.
2. Select the latest corporate-action revision per action ID available by `decision_at`.
3. Remove an action only when its selected revision is `CANCELLED`.
4. Select the latest valuation per `(action_id, purpose)` available by `decision_at`.
5. Select the latest coverage record available by `decision_at`.
6. Reject future fallback, same-key conflicts, incomplete coverage, missing lineage, and invalid currencies.

## Action range

Actions before the first selected raw bar are already embodied in the opening price and are ignored for this build.

A continuing action on the first selected bar is rejected because its period return cannot be reconstructed without a prior bar.

## Forward total-return index

Initialize the first valid bar to 100. For each later bar:

```text
TRI[t] = TRI[t-1] × GrossReturn[t]
```

For a normal session:

```text
GrossReturn[t] = RawClose[t] / RawClose[t-1]
```

For a continuing corporate-action session:

```text
GrossReturn[t] = (
    RawClose[t] × ShareMultiplier[t]
    + CashDistribution[t]
    + NonCashDistributionValue[t]
) / RawClose[t-1]
```

For a terminal event after the last parent bar:

```text
GrossReturn[terminal] = TerminalValue / LastParentRawClose
```

The output availability timestamp is the maximum availability of the cumulative prior result and all new inputs.

## Back-adjusted audit series

Traverse daily bars backward from the latest selected bar. The latest raw close has factor one. After recording the action-session close, multiply cumulative factors for observations before that session.

This yields:

- cumulative split factor;
- cumulative total-return factor;
- split-adjusted close;
- total-return-adjusted close;
- action IDs and snapshots applied to each historical value;
- deterministic adjustment version hash.

## Phase 01 bridge

The Phase 01 strategy receives:

```text
adjusted_close = forward total-return index
price_eligibility_close = current raw close
```

The forward index has an arbitrary level, but momentum ratios, daily returns, volatility, SMA comparisons, and correlations are invariant to constant scaling.

The price threshold is evaluated from `price_eligibility_close`, preventing a later split or accumulated dividend from rewriting historical eligibility.

## Determinism

The build hash covers:

- instrument ID;
- decision timestamp;
- reporting currency;
- selected raw bars;
- selected corporate actions;
- selected valuations;
- selected coverage record;
- derived event factors.

Identical inputs produce an identical hash. A correction, cancellation, valuation revision, or coverage revision creates a different hash and a new dataset version.

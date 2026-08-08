# Regulatory Fee Basis Contract

**Version:** 0.2.0  
**Frozen:** 2026-08-08  
**Coverage:** 2010-01-01 through 2026-08-08

## Contract purpose

Provide an immutable, effective-dated regulatory-equivalent cost basis for covered U.S. equity sales in Phase 03.

## Inputs

For each simulated sell execution:

- `trade_date`;
- `shares` as a positive integer;
- `execution_price` as a positive decimal;
- exactly one Section 31 entry covering `trade_date`;
- exactly one FINRA TAF entry covering `trade_date`.

## Section 31 contract

Fields:

- `effective_from`;
- `effective_to`;
- `usd_per_million`;
- `source_reference`.

Rules:

1. Rate must be non-negative.
2. Intervals must be contiguous and non-overlapping over the frozen range.
3. Selection is by trade date.
4. Section 31 component is calculated as sale notional × rate / 1,000,000.
5. The model represents the official regulatory-equivalent rate, not a claim about exact historical broker customer rounding.

## FINRA TAF contract

Fields:

- `effective_from`;
- `effective_to`;
- `usd_per_share`;
- `maximum_usd_per_trade`;
- `source_reference`.

Rules:

1. Per-share rate and cap must be non-negative.
2. Intervals must be contiguous and non-overlapping over the frozen range.
3. Selection is by trade date.
4. TAF applies only to covered sales represented by the strategy's U.S. equity execution model.
5. TAF equals `min(shares × per_share_rate, cap)`.
6. If the execution price per share is below the applicable per-share TAF rate, the TAF component is zero.

## Composition

The independent official schedules are composed into `RegulatoryFeeScheduleEntry` intervals at every rate boundary. Composition must be deterministic for identical source config.

## Phase 03 acceptance-period rule

The final acceptance period must satisfy:

```text
2010-01-01 <= acceptance_start <= acceptance_end <= 2026-08-08
```

If a later end date is required, official rates must be refreshed, reviewed, versioned, and the schedule re-frozen before the run.

## Reproducibility metadata

The Phase 03 run manifest must contain:

- regulatory fee config version;
- SHA-256 of `configs/data/regulatory_fee_basis.yaml`;
- acceptance start/end;
- effective composed fee schedule hash or equivalent deterministic lineage;
- transaction-cost model version.

## Prohibited behavior

- backfilling the current fee rate across all history;
- silently extrapolating beyond the frozen interval;
- selecting a rate based on when the backtest is executed rather than the historical trade date;
- changing the schedule after inspecting Phase 03 results without registering a new dataset/model version;
- claiming exact historical Schwab invoice equivalence from this regulatory schedule.

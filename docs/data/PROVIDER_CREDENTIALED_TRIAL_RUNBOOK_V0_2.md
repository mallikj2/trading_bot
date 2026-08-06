# Provider Credentialed Trial Runbook v0.2

**Date:** 2026-08-05  
**Status:** Ready to run; credentials not present in the validation environment

## 1. Required environment

```bash
export MASSIVE_API_KEY='...'
export SEC_USER_AGENT='QuantTradingBot/0.2 monitored-contact@example.com'
```

The contact email must be real and monitored. Never commit either value.

## 2. Environment check

```bash
PYTHONPATH=src python -m trading_bot.data.adapters.trial environment-status
```

Both values must report `AVAILABLE` before a credentialed run can pass.

## 3. Smoke run

```bash
PYTHONPATH=src python -m trading_bot.data.adapters.trial smoke \
  --ticker AAPL \
  --cik 0000320193 \
  --as-of-date 2025-12-31 \
  --output artifacts/provider_trial/smoke.json
```

The smoke test verifies authentication and top-level response identity only. It is not the representative-case acceptance test.

## 4. Representative-case run

Use `configs/data/provider_representative_cases.yaml` and persist every response through `RawSnapshotStore` before normalization.

For each request record:

- endpoint and redacted parameters;
- retrieved timestamp;
- provider request ID;
- record count;
- response hash;
- normalized count;
- rejected count and reason;
- coverage start/end;
- adapter version;
- schema version;
- license classification.

## 5. Mandatory validations

### Ticker snapshots

- Query both `active=true` and `active=false` for historical dates.
- Demonstrate that a later listing or delisting does not alter an earlier snapshot.
- Verify CIK/FIGI stability.
- Verify five delisted cases and a ticker-reuse case.

### Ticker events

- Validate at least five identity changes.
- Use a stable identifier rather than a current ticker when possible.
- Fail on unsupported event types.

### Daily and minute aggregates

- Request `adjusted=false`.
- Reconcile session dates with the versioned exchange calendar.
- Validate two early-close sessions.
- Validate complete and incomplete 10:00–10:30 ET windows.

### Corporate actions

- Validate five split/reverse-split cases.
- Validate five cash-dividend cases.
- Reconcile dates and ratios against raw-price discontinuities.
- Preserve unknown merger/spinoff events as blockers.

### Market cap and sector

- Query the same ticker overview on multiple historical dates.
- Compare returned market cap and SIC with dated source evidence.
- Do not enable `validated_historical_as_of_semantics` until the evidence report is approved.

### SEC shares

- Fetch submissions, all listed older fragments required for the research interval, and company facts.
- Join facts to exact acceptance timestamps.
- Validate at least one amended filing.
- Validate a multi-class issuer and confirm ambiguity blocks rather than sums silently.

## 6. License gate

Before storing a full history, record written confirmation of:

- local storage rights;
- historical research/backtesting rights;
- retention after subscription cancellation;
- derived-data rights;
- redistribution restrictions;
- API versus flat-file differences.

The trial cannot receive final PASS while this gate is pending.

## 7. Expected decision

- `PASS`: all required capabilities and licenses evidenced.
- `CONDITIONAL PASS`: code and most fields pass, with named non-strategy-critical gaps.
- `FAIL`: survivorship, PIT, identity, VWAP, or retention requirements cannot be met.

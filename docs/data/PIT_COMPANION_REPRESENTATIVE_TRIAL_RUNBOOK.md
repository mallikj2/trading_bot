# PIT Security-Master and Exact-Execution Representative Trial Runbook

## Purpose

Produce the external evidence needed for P02-G18 and the companion portion of P02-G04 without changing strategy rules.

## Prerequisites

Set only after account/license review:

```bash
export DATABENTO_API_KEY='...'
export DATABENTO_RESEARCH_LICENSE_APPROVED=true
export DATABENTO_EXECUTION_DATASET='<approved dataset>'
export DATABENTO_EXECUTION_COVERAGE_APPROVED=true
```

The final flag means the dataset's lit/off-exchange historical coverage has been reviewed against the Phase 01 execution benchmark. It must not be set merely because the dataset has a `trades` schema.

## Step 1 — Environment check

```bash
PYTHONPATH=src python -m trading_bot.data.adapters.pit_companion_trial environment-status
```

Expected before approval: `trial_ready=false`.

## Step 2 — Single-case smoke

```bash
PYTHONPATH=src python -m trading_bot.data.adapters.pit_companion_trial smoke \
  --ticker AAPL \
  --as-of-date 2025-12-31 \
  --output PIT_COMPANION_TRIAL_RESULTS.json
```

The smoke must prove that the as-of identity record is known by `ts_record`, contains a stable identifier and CIK, and produces trade-level 10:00–10:30 ET VWAP from the configured dataset.

## Step 3 — Security-master representative panel

Execute the machine-readable criteria in:

`configs/data/pit_security_master_execution_acceptance.yaml`

Minimum evidence includes:

- 10 active listings;
- 5 historical delistings;
- 5 symbol-change sequences;
- at least 1 ticker-reuse example;
- 5 non-common-stock exclusions;
- 25 randomly selected identity records reviewed against source/reference evidence.

For each case retain the raw provider snapshot, request metadata, normalized row, decision timestamp, and selected as-of record.

## Step 4 — Point-in-time leakage tests

For revised records, query decisions immediately before and after `ts_record`.

Required behavior:

```text
before ts_record -> prior version or NULL
after ts_record  -> revised version may become visible
```

`ts_effective` alone must never authorize a future-recorded revision.

## Step 5 — Sector-blind monthly ledger

Build monthly `UniverseInput` rows using the frozen Phase 01 rules and call:

```python
build_sector_blind_target_ledger(...)
write_sector_target_ledger(...)
```

Required acceptance:

- every otherwise-eligible row is retained irrespective of sector availability;
- every target has PIT CIK and stable identity;
- no current ticker list is used;
- ledger is directly accepted by the SEC crawler's `parse_target_ledger()`.

This artifact becomes the denominator for P02-G07.

## Step 6 — Exact-execution panel

At least 20 sessions:

- 5 EST sessions;
- 5 EDT sessions;
- 5 high-liquidity examples;
- 5 lower-liquidity examples that still satisfy the strategy universe.

For every case retain:

- stable input identifier used in request;
- exact UTC request window;
- selected dataset and coverage profile;
- raw trade snapshot;
- quality-flag counts;
- included trade count and size;
- computed size-weighted VWAP.

A dataset with partial venue coverage may only be used if the benchmark is explicitly accepted as equivalent to the frozen Phase 01 requirement. Otherwise P02-G18 remains BLOCKED.

## Step 7 — Account/retention evidence

Archive the account-specific terms or approval record confirming the private non-display research use and retained snapshots required for reproducibility.

Public pricing or generic marketing text is not sufficient evidence of project-specific retention rights.

## PASS criteria

P02-G18 may become PASS only when all of the following are true:

1. project account/license approved;
2. immutable retention/reproducibility rights approved;
3. security-master panel passes;
4. execution coverage profile approved;
5. exact-execution panel passes;
6. sector-blind target ledger is generated without unresolved identities;
7. all raw evidence and hashes are retained.

Until then Phase 03 remains unauthorized.

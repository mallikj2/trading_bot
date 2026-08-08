# Validation Results — Phase 02 PIT Security-Master and Exact-Execution Integration

**Date:** 2026-08-08  
**Task status:** `ENGINEERING PASS / CREDENTIALED EVIDENCE BLOCKED`  
**P02-G04:** `BLOCKED`  
**P02-G18:** `BLOCKED`  
**Phase 02 status:** `ACTIVE — NOT READY FOR PHASE 03`

## Cumulative automated tests

Command:

```bash
PYTHONPATH=src pytest -q
```

Result:

```text
287 passed, 12 subtests passed
```

This includes the approved Phase 01 strategy tests and the full cumulative Phase 02 stack.

## Focused PIT companion / target-ledger tests

Command:

```bash
PYTHONPATH=src pytest -q \
  tests/unit/data/adapters/test_databento_companion.py \
  tests/unit/data/adapters/test_databento_pit_execution.py \
  tests/unit/data/adapters/test_core_trial.py \
  tests/unit/data/adapters/test_pit_companion_trial.py \
  tests/unit/data/test_pit_acceptance.py \
  tests/integration/data/test_pit_companion_sector_ledger.py
```

Result:

```text
20 passed
```

Focused coverage includes:

- approval-gated Databento SDK client construction;
- US common-equity security-master filtering;
- separate `ts_effective` and `ts_record` handling;
- future provider-record exclusion;
- PIT primary-listing selection;
- ticker-reuse detection;
- stable FIGI historical execution queries;
- EST/EDT-correct 10:00–10:30 ET execution windows;
- exact trade-size-weighted VWAP;
- bad timestamp/book-quality rejection;
- mixed provider-instrument rejection;
- sector-blind monthly universe behavior;
- PIT CIK/exchange/security-type cross-checks;
- PIT shares-outstanding market-cap corroboration;
- direct sector-ledger compatibility with the SEC crawler;
- fail-closed credential/license/execution-coverage governance.

## Credentialed runner invocation

The standalone companion runner was invoked with external secrets intentionally absent:

```bash
env -u DATABENTO_API_KEY \
    -u DATABENTO_RESEARCH_LICENSE_APPROVED \
    -u DATABENTO_EXECUTION_DATASET \
    -u DATABENTO_US_EQUITIES_DATASET \
    -u DATABENTO_EXECUTION_COVERAGE_APPROVED \
  PYTHONPATH=src python -m trading_bot.data.adapters.pit_companion_trial smoke \
    --ticker AAPL \
    --as-of-date 2025-12-31 \
    --output PIT_COMPANION_TRIAL_RESULTS.json
```

Result: exit code `2`, `BLOCKED`.

The runner requires:

```text
DATABENTO_API_KEY
DATABENTO_RESEARCH_LICENSE_APPROVED=true
DATABENTO_EXECUTION_DATASET=<approved dataset>
DATABENTO_EXECUTION_COVERAGE_APPROVED=true
```

No PIT provider coverage, execution coverage, license, or VWAP accuracy claim is made from offline fixtures.

## End-to-end integration evidence

The integration test validates this chain without vendor fabrication:

```text
PIT security-master record
    -> immutable internal instrument identity
    -> sector-blind Phase 01 monthly universe target
    -> P02-G07 SEC target-ledger payload
    -> SEC crawler target-ledger parser

stable instrument identity
    -> trade-level 10:00–10:30 ET records
    -> exact size-weighted VWAP
```

The target-ledger path deliberately removes only the sector requirement. Missing PIT CIK for an otherwise eligible security blocks the build instead of shrinking the P02-G07 denominator.

## Compilation and artifact parsing

- Python `compileall`: PASS
- YAML parse: PASS
- JSON parse: PASS
- Gate audit: 18 mandatory = 11 PASS / 7 BLOCKED / 0 CONDITIONAL
- Phase 03 authorization: FALSE

## Current gate conclusions

### P02-G04

**BLOCKED** until the paid/composite core-provider representative trial is completed.

### P02-G18

**BLOCKED** until:

1. account-specific research and retention rights are approved;
2. the execution dataset is explicitly selected;
3. the historical venue/off-exchange execution coverage profile is approved;
4. the security-master representative panel passes;
5. the exact execution representative panel passes;
6. a real sector-blind monthly target ledger is produced from credentialed PIT data.

### P02-G07 dependency

The internal sector-blind ledger builder is now complete, but the real ledger still depends on P02-G04/P02-G18 external evidence. The SEC monitored-contact crawl remains separately required.

### Phase 03

**NOT AUTHORIZED**

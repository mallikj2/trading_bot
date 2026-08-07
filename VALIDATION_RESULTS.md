# Validation Results — Phase 02 Historical Short-Borrow Modeling

**Date:** 2026-08-06  
**Task status:** `IMPLEMENTATION PASS / SOURCE AND LIVE-BROKER GATES BLOCKED`

## Automated tests

Command:

```bash
PYTHONPATH=src pytest -q
```

Result:

```text
188 passed, 12 subtests passed
```

The cumulative suite includes the approved Phase 01 strategy tests and all Phase 02 data-kernel, provider-adapter, sector, corporate-action, earnings, spread/cost, and new short-borrow tests.

## New short-borrow focused coverage

The new tests cover:

- future borrow revisions excluded from earlier decisions;
- expired borrow records not carried forward;
- conflicting same-revision observations rejected;
- regulatory proxy data prohibited from asserting availability;
- missing fee rate blocks entry;
- insufficient available quantity blocks entry;
- hard-to-borrow policy is explicit;
- live gate rejects market-composite evidence;
- known recall/restriction blocks immediately;
- future-unknown recall does not leak backward;
- rate/economic ceiling enforcement;
- EOD market value × annual rate / 360 × calendar-day fee calculation;
- Phase 01 2x pessimistic borrow-cost multiplier;
- explicit dense source coverage semantics;
- existing-short forced exit when borrow evidence expires;
- AVAILABLE-to-UNAVAILABLE withdrawal event derivation;
- ORTEX non-demo license gate;
- ORTEX historical ticker-resolution request parameters;
- ORTEX date-specific availability request construction;
- research/live evidence separation in the integration bridge.

## Compilation and artifact parsing

- Python `compileall`: PASS
- YAML parse: 9 files PASS
- JSON parse: 4 files PASS

## Evidence not claimed

The following were not available and are therefore **not** claimed as passed:

- licensed historical securities-lending provider coverage;
- provider raw-retention approval;
- credentialed S&P Global/DataLend/ORTEX sample;
- historical recall-event completeness;
- Schwab account short permission;
- Schwab credentialed current shortability/HTB/rate/quantity/locate contract;
- live short-order execution.

## Gate result

### Engineering

**PASS**

### Historical borrow source

**BLOCKED / OPEN**

### Live Schwab borrow/account gate

**BLOCKED / OPEN**

### Phase 02 overall

**ACTIVE**

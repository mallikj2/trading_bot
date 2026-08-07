# Validation Results — Phase 02 Financing / Cash Carry + Data-Gate Audit

**Date:** 2026-08-06  
**Task status:** `IMPLEMENTATION PASS / PHASE 02 NOT READY FOR PHASE 03`

## Cumulative automated tests

Command:

```bash
PYTHONPATH=src pytest -q
```

Result:

```text
205 passed, 12 subtests passed
```

The cumulative suite includes the approved Phase 01 strategy tests and all Phase 02 kernel, provider adapter, sector, corporate action/total return, earnings, spread/cost, short-borrow, financing, and gate-audit tests.

## New focused tests

```text
17 passed
```

Coverage includes:

- zero primary cash carry;
- short proceeds cannot be reused;
- gross leverage > 1.0 rejection;
- positive settled debit rejection;
- broker-specific evidence required for any future positive broker cash credit or margin debit;
- future financing rate revisions excluded;
- optional DTB3-style benchmark attribution does not alter primary return;
- pessimistic multiplier applies to financing costs only;
- machine-readable Phase 02 gate counts;
- blocked/conditional mandatory gates deny Phase 03 authorization;
- duplicate/invalid gate definitions fail closed;
- integration of matched-gross strategy accounting with restricted short collateral.

## Approved Phase 01 regression

```text
20 passed
```

## Compilation and artifact parsing

- Python `compileall`: PASS
- YAML parse: 11 files PASS
- JSON parse: 5 files PASS
- Machine-readable audit: 17 mandatory gates = 9 PASS / 7 BLOCKED / 1 CONDITIONAL
- All audit evidence file references: present
- SHA-256 manifest: PASS
- ZIP integrity: PASS

## Evidence not claimed

The following remain open and are **not** claimed as passed:

- approved core provider research/retention license;
- credentialed representative-case core provider trial;
- full historical-sector coverage crawl;
- complex corporate-action provider reconciliation;
- licensed historical earnings revision sample;
- licensed observed-spread calibration dataset/panel;
- licensed historical securities-lending coverage;
- full acceptance-period regulatory fee basis;
- Schwab live short/account/borrow authorization;
- Schwab live cash-feature/margin contract testing.

## Gate result

### Financing/cash-carry engineering

**PASS**

### Phase 02 final data gate

**NOT READY**

### Phase 03 final acceptance backtest

**NOT AUTHORIZED**

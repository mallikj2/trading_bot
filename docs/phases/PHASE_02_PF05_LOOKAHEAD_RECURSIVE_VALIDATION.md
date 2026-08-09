# Phase 02B — P02-PF05 Lookahead + Recursive Validation

**Date:** 2026-08-08  
**Status:** PASS  
**Phase 02:** ACTIVE  
**Procurement authorized:** NO  
**Phase 03 authorized:** NO

## Objective

Add an adversarial strategy-validation layer before OMS/simulation and before purchasing commercial data. The validator must demonstrate that the frozen CSMOM-LS-v0.2 reference implementation does not use future rows and that its historical decision outputs are stable across approved warm-up windows.

## Delivered

### Canonical decision snapshots

Each decision snapshot hashes six sections independently:

- features;
- universe;
- cross-sectional ranking;
- candidates;
- targets;
- exits when an exit evaluator is supplied.

This makes failures localizable rather than reducing the entire strategy decision to one opaque hash.

### Lookahead validator

For each selected decision date, PF05 compares the decision produced with the full supplied panel against the decision produced after removing every row after that date.

Any difference fails the analysis.

### Recursive validator

PF05 recomputes the same historical decision using trailing 300-, 320-, and 360-session windows and compares them with the full history available at that decision time.

### Adversarial controls

The test suite deliberately injects:

- future-row ranking dependence;
- arbitrary history-start dependence;
- future-dependent exit logic.

All contaminated controls fail as required.

### Research Console integration

The read-only console now includes a **Validation** screen and `GET /api/v1/strategy-validation` endpoint showing synthetic PF05 status. The API remains mutation-free and does not imply Phase 03 approval.

## Numeric tolerance finding

A clean recursive run exposed a machine-level difference in an otherwise identical 200-day moving average at approximately the 12th decimal place. PF05 therefore canonicalizes comparison output to 10 decimal places.

This affects only validation serialization/hashing; it does not alter strategy calculations.

## Acceptance result

Clean synthetic CSMOM controls:

```text
LOOKAHEAD = PASS
RECURSIVE = PASS
```

Contaminated controls:

```text
FUTURE_ROW_RANK_DEPENDENCY = FAIL AS EXPECTED
ARBITRARY_HISTORY_START_DEPENDENCY = FAIL AS EXPECTED
FUTURE_DEPENDENT_EXIT = FAIL AS EXPECTED
```

The machine evidence is stored in `PF05_STRATEGY_VALIDATION_RESULTS.json`.

## Governance

PF05 does not modify any approved Phase 01 strategy rule. It does not weaken any of the existing Phase 02 external data gates.

```text
PROCUREMENT_AUTHORIZED=false
PROCUREMENT_READY_FOR_MANUAL_APPROVAL=false
PHASE03_AUTHORIZED=false
LIVE_TRADING_AUTHORIZED=false
```

## Out of scope

- OMS and simulated broker — PF06;
- deterministic simulation runtime — PF07;
- experiment registry/reporting — PF08;
- alerts/incident center — PF09;
- recovery/reconciliation simulation — PF10;
- commercial-provider credentialed evidence;
- acceptance backtesting;
- deployed paper/live trading.

## Gate result

**P02-PF05 = PASS**

`P02-PF-GATE` remains blocked because PF06–PF10 remain incomplete.

**Next task: P02-PF06 — OMS + SimulatedBroker.**

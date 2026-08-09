# Phase 02B — P02-PF08 Experiment Registry + Reporting + Attribution

**Gate result:** PASS  
**Date:** 2026-08-08  
**Next task:** P02-PF09 Alerts + Incident Center

## Objective

Create a provenance-first, immutable experiment and reporting foundation before any licensed acceptance data is purchased. PF08 must make future Phase 03 runs comparable and reproducible without claiming that synthetic Phase 02 fixtures prove strategy profitability.

## Delivered

- deterministic experiment definitions bound to strategy/version, code commit, dataset/universe/parameter manifests, cost-model version, period, and random seed;
- append-only SQLite experiment registry with UPDATE/DELETE denial;
- deterministic run IDs and independent result hashes;
- required artifact/source-runtime hashes for every run;
- explicit evidence classes with `PHASE03_ACCEPTANCE` prohibited in PF08;
- long-side and short-side attribution;
- spread/slippage/regulatory/borrow cost attribution;
- baseline-vs-scenario delta reporting with no automatic winner selection;
- synthetic baseline, 2x-cost, and delayed-execution fixtures;
- Research Console `Experiments` page and GET-only API endpoint;
- local CLI to construct/verify the fixture registry and report.

## Major governance decisions

### Provenance precedes performance

A run cannot be registered without immutable provenance. Metrics without their exact strategy, code, data/universe/parameter/cost inputs are not considered experiment evidence.

### PF08 synthetic metrics are not strategy evidence

Every committed PF08 report is labeled:

```text
NOT_STRATEGY_EVIDENCE
```

The API explicitly returns:

```text
strategy_profitability_validated=false
phase03_acceptance_backtest=false
```

PF08 refuses to register `PHASE03_ACCEPTANCE` evidence.

### No automatic winner selection

Scenario comparisons report deltas versus a declared baseline. PF08 does not optimize parameters, rank experiments by Sharpe, or choose a strategy configuration. Those activities require preregistered Phase 03 governance.

## Acceptance evidence

- immutable definition IDs are deterministic;
- immutable run/result hashes survive registry close/reopen;
- duplicate identical registration is idempotent;
- conflicting/tampered storage fails verification;
- net-return reporting must exactly reconcile to long + short + cost attribution;
- positive "cost" components are rejected;
- synthetic scenarios render through the read-only Research Console;
- no broker/provider credentials are required.

## Governance

PF08 does not change:

```text
PROCUREMENT_AUTHORIZED=false
PROCUREMENT_READY_FOR_MANUAL_APPROVAL=false
PHASE03_AUTHORIZED=false
```

No strategy profitability, acceptance-backtest, paper-trading, or live-trading result is claimed.

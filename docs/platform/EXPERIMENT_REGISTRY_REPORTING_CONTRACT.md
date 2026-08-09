# Experiment Registry, Reporting, and Attribution Contract

## 1. Definition identity

An experiment definition is content-addressed from:

- experiment name and scenario;
- strategy ID/version;
- stated purpose;
- code commit/reference;
- dataset manifest hash;
- universe manifest hash;
- parameter manifest hash;
- transaction-cost model version;
- acceptance start/end dates;
- deterministic random seed.

Changing any field creates a different `definition_id`.

## 2. Run identity and result hash

A run binds the definition to:

- evidence class;
- start/completion timestamps;
- deterministic runtime/state hash;
- result hash.

The result hash independently covers metrics, attribution, and result-artifact hashes. A run is not considered reproducible if any referenced hash is absent.

## 3. Append-only registry

`SQLiteExperimentRegistry` denies UPDATE/DELETE through database triggers. Re-registering identical content is idempotent. Same-ID conflicting content or failed hash verification blocks the registry.

## 4. Required reporting metrics

PF08's schema requires at least:

- `net_return_bps`;
- `benchmark_return_bps`;
- `max_drawdown_bps`;
- `sharpe`;
- `turnover_bps`.

This schema does not imply that those values have Phase 03 acceptance validity.

## 5. Attribution identity

For every run:

```text
gross_return_bps = long_contribution_bps + short_contribution_bps
net_return_bps   = gross_return_bps + sum(cost_components_bps)
```

Cost components must be zero or negative. A mismatched net metric is rejected.

## 6. Comparison policy

Comparisons are baseline-relative and deterministic. The registry may report metric/cost deltas, but it may not automatically select a winner or modify the frozen strategy.

## 7. Phase boundary

During PF08 only `SYNTHETIC_FIXTURE` and `SIMULATION_ONLY` evidence is allowed. `PHASE03_ACCEPTANCE` is rejected by contract.

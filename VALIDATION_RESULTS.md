# Validation Results — Phase 02 Complex Corporate Actions and Point-in-Time Total Return

**Validated:** 2026-08-05 America/New_York  
**Task result:** IMPLEMENTATION PASS / PROVIDER COVERAGE CONDITIONAL  
**Phase result:** ACTIVE

## Scope

Validation covered the cumulative repository overlay containing:

- the approved Phase 01 `CSMOM-LS-v0.2` reference strategy;
- the Phase 02 minimum data kernel;
- production Massive and SEC adapters;
- filing-level historical sector classification;
- complex corporate-action and point-in-time total-return processing.

No credentialed Massive payload, provider retention approval, or full-universe complex-action coverage report was available. No provider completeness or accuracy claim is made.

## Full merged regression

Command:

```bash
PYTHONPATH=src python -m pytest -q
```

Result:

```text
119 passed, 12 subtests passed in 12.41s
```

## Test breakdown

Phase 01 strategy suite:

```text
20 passed
```

This comprises the 19 previously approved strategy tests plus one Phase 02 interface test proving that `price_eligibility_close` is separate from the total-return `adjusted_close` series.

Phase 02 data and integration suite:

```text
99 passed, 12 subtests passed
```

New corporate-action coverage includes:

- two-for-one split and reverse-split economics;
- future split invisibility at an earlier decision;
- cash-dividend total return and short liability;
- stock-dividend quantity and price factors;
- spinoff valuation and signed child positions;
- cash-and-stock merger terminal return and successor position;
- explicit zero-recovery delisting;
- action cancellation and later revision behavior;
- incomplete coverage rejection;
- unsupported tender and rights-event policy;
- missing ex-date and prior-bar rejection;
- currency mismatch rejection;
- deterministic build and position-effect hashes;
- reconciliation of back-adjusted returns with the forward total-return index;
- split-safe raw dollar volume through the Phase 01 feature pipeline;
- absence of artificial split and dividend momentum jumps;
- six machine-readable registered economic-event fixtures.

## Compilation

Command:

```bash
PYTHONPATH=src python -m compileall -q src tests
```

Result: PASS.

## Configuration parsing

Six YAML files parsed successfully:

```text
configs/data/corporate_action_total_return.yaml
configs/data/historical_sector_classification.yaml
configs/data/minimum_data_kernel.yaml
configs/data/production_provider_adapters.yaml
configs/data/provider_representative_cases.yaml
configs/strategies/csmom_ls_v0_2.yaml
```

## Determinism and integrity

- identical selected inputs produce identical `build_hash` values;
- revised corporate-action inputs change the build hash;
- same-key conflicting revisions fail closed;
- raw files and provider snapshots remain immutable;
- all package files are covered by `MANIFEST.sha256`;
- manifest verification and ZIP integrity checks passed.

## Important interface correction

The approved strategy previously used `adjusted_close` both for total-return features and the USD 10 price threshold. The normalized Phase 02 interface now provides:

```text
adjusted_close = forward total-return index
price_eligibility_close = current-session raw close
```

This preserves the intended strategy economics while preventing a later split or accumulated distribution from rewriting historical price eligibility. Backward compatibility remains for development callers that omit the new field, but research-tier data must supply it.

## Remaining external evidence

- credentialed Massive representative-case trial;
- provider storage and post-cancellation retention approval;
- representative provider reconciliation for splits and dividends;
- at least one provider-sourced merger and spinoff reconciliation;
- delisting and terminal-value coverage samples;
- full-universe action-coverage completeness statistics;
- full SEC historical-sector coverage scan;
- revision-aware historical earnings schedules;
- spread calibration;
- short-borrow availability and fee modeling.

Phase 03 final acceptance testing, paper trading, and live trading remain unauthorized.

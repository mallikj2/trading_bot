# Phase 02 — Complex Corporate Actions and Point-in-Time Total Return

**Version:** 0.1  
**Date:** 2026-08-05  
**Task status:** IMPLEMENTATION PASS / PROVIDER COVERAGE CONDITIONAL  
**Phase status:** ACTIVE

## 1. Objective

Implement the point-in-time corporate-action and return layer required by Phase 01 without relying on retrospectively adjusted provider prices.

## 2. Completed scope

- extended action types and lifecycle status;
- latest-known revision and cancellation semantics;
- explicit complete-coverage contract;
- raw, split-adjusted, total-return-adjusted, and forward-index separation;
- splits and reverse splits;
- cash and stock dividends;
- spinoff distribution valuation;
- cash and stock merger/acquisition consideration;
- delisting, liquidation, bankruptcy, and explicit zero recovery;
- terminal return observations;
- signed long/short cash and security distributions;
- deterministic action, factor, position-effect, and build hashes;
- Phase 01 bridge separating price eligibility from the total-return series;
- adversarial unit and end-to-end integration tests.

## 3. Core decisions

### 3.1 No provider-adjusted black box

Raw prices remain immutable. Adjustments are derived from normalized, revision-aware action and valuation records.

### 3.2 Complete coverage is evidence

An empty action result is accepted only when accompanied by an available, complete coverage record extending through the decision timestamp and declaring all required action types.

### 3.3 Current price eligibility is separate

Phase 01 previously reused `adjusted_close` for both return features and the USD 10 threshold. Phase 02 now preserves the approved economics with two fields:

- `adjusted_close`: forward total-return index for return features;
- `price_eligibility_close`: current raw close for the point-in-time USD 10 threshold.

The strategy remains backward-compatible when the new field is absent, but normalized Phase 02 research data must provide it.

### 3.4 Complex events require valuation evidence

Spinoffs and stock consideration are not assigned an inferred value. Missing point-in-time valuation blocks the build. Currency mismatch also blocks because FX conversion is not implemented.

### 3.5 Terminal events stop the parent series

A terminal return is calculated from explicit cash plus noncash consideration relative to the last parent raw close. The parent quantity becomes zero, with successor security quantities recorded separately.

## 4. Acceptance evidence

- 99 Phase 02 tests passed when run without the Phase 01 strategy suite;
- 20 original approved Phase 01 strategy tests plus the new interface-separation test passed;
- 119 total tests passed in the cumulative repository overlay;
- 12 existing taxonomy boundary subtests passed;
- Python compilation passed;
- YAML parsing passed;
- deterministic manifest and ZIP validation passed.

## 5. Limitations and remaining evidence

This task does not prove that the selected provider supplies complete and historically correct complex-action records.

Before final Phase 02 PASS, required external evidence remains:

1. credentialed representative-case trial;
2. provider storage and post-cancellation retention approval;
3. at least five split/reverse-split reconciliations;
4. at least five cash-dividend reconciliations;
5. at least one merger and one spinoff with independent consideration checks;
6. delisting/terminal-value samples;
7. full-universe action-coverage completeness statistics;
8. SEC sector coverage evidence;
9. revision-aware historical earnings schedules;
10. spread calibration;
11. short-borrow model and assumptions.

Tender offers and rights distributions remain unsupported and block affected instruments.

## 6. Gate decision

### Implementation: PASS

The contracts, engine, strategy interface, position transformations, lineage, and adversarial tests are ready for merge.

### Provider coverage: CONDITIONAL

No credentialed action payload or retention-license approval was available in this environment. No provider completeness or accuracy claim is made.

### Phase 02: ACTIVE

Phase 03 final acceptance testing, paper trading, and live trading remain unauthorized.

## 7. Next task

Proceed with the revision-aware historical earnings schedule contract and source evaluation while the credentialed provider/license gate remains open.

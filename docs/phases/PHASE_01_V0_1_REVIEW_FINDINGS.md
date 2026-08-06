# Phase 01 v0.1 Review Findings

`CSMOM-LS-v0.1` is superseded by `CSMOM-LS-v0.2` before approval.

Material defects corrected in v0.2:

1. Vacuous candidate tests that passed with zero selected securities.
2. Adjusted-close multiplied by raw-volume liquidity calculation.
3. Unspecified behavior when only one side had sufficient candidates.
4. Hard-coded decision time that did not handle early closes.
5. Undefined final research fill benchmark.
6. Incomplete earnings handling for existing positions.
7. Unfrozen statistical sensitivity grid and regime definitions.
8. Undefined metric formulas and turnover conventions.
9. YAML/runtime drift risk.
10. Ticker-keyed history rather than stable instrument identity.
11. Reversed presentation order for selected short ranks.
12. Missing deterministic whole-share neutrality repair.

The v0.1 strategy direction was not rejected for poor performance; it was rejected as an incomplete specification before valid performance testing.

# Lookahead + Recursive Validation Contract

**Task:** P02-PF05  
**Strategy:** CSMOM-LS-v0.2  
**Mode:** Phase 02 pre-purchase platform foundation

## Purpose

PF05 adds an independent adversarial validator around the frozen strategy implementation. It does **not** change strategy formulas. Its job is to prove that an earlier research decision is invariant to information that arrived later and is stable once the approved history requirement has been satisfied.

The validator compares six deterministic decision sections:

1. decision-date features;
2. eligible universe membership;
3. full cross-sectional ranking;
4. selected long/short candidates;
5. portfolio target weights;
6. optional exit decisions supplied by an exit evaluator.

A difference in any required section is a validation failure.

## Lookahead analysis

For each historical decision date `t`:

```text
reference  = evaluate(all supplied rows, t)
challenger = evaluate(rows with session_date <= t, t)
```

The following invariant is mandatory:

```text
reference(t) == challenger(t)
```

This is stricter than checking only the final candidate list. A future row changing an intermediate feature, universe membership, rank, target, or exit decision fails the analysis even if another downstream rule happens to mask the difference.

PF05 does not replace Phase 02 point-in-time source validation. If a future fact has already been incorrectly written into a historical row, source-level `available_at`/decision-time controls remain responsible for detecting that contamination. PF05 detects **algorithmic dependence on future rows**.

## Recursive analysis

For each decision date, the strategy is first evaluated using all history available through that date. It is then recomputed using multiple approved trailing history windows.

Current frozen windows:

```text
300 sessions
320 sessions
360 sessions
```

All windows are at or above the Phase 01 minimum 300-session history requirement.

The decision sections must remain equal after canonical numeric normalization. `valid_session_count` itself is intentionally excluded from the comparison because its absolute value necessarily changes when the start of the supplied history changes; its trading consequence is captured through `base_eligible`.

## Numeric comparison policy

PF05 canonicalizes floating-point reporting values to **10 decimal places** before hashing/comparison.

This does not modify strategy calculations. It prevents false recursive failures caused by machine-level rolling-window accumulation differences such as two mathematically identical 200-day averages differing only around the 12th decimal place.

Any difference remaining after this normalization is treated as material for PF05 and fails closed.

## Exit validation

The validator supports an injected deterministic exit evaluator. When provided, its point-in-time output is included as the `EXITS` section and is subject to the same full-vs-truncated and recursive comparisons.

This enables PF07/later holding-state logic to reuse PF05 without modifying the validator.

## Required adversarial controls

PF05 acceptance requires both positive and negative controls:

- clean CSMOM fixture → lookahead PASS;
- clean CSMOM fixture → recursive PASS;
- intentionally future-dependent ranking → lookahead FAIL;
- intentionally history-start-dependent feature → recursive FAIL;
- intentionally future-dependent exit decision → lookahead FAIL.

A validator that only passes clean data but cannot fail the contaminated controls is not acceptable.

## Determinism

Rows are canonicalized and deterministically ordered before section hashing. Input row order must not change the validation result or suite hash.

## Governance boundaries

PF05 may not:

- change CSMOM-LS-v0.2 thresholds, weights, features, rankings, or execution rules;
- accept a future-data difference because performance looks better;
- authorize Phase 03;
- submit orders;
- connect to a broker;
- require commercial market-data credentials.

PF05 synthetic PASS means the validator framework and current frozen reference implementation passed the pre-purchase controls. The final acceptance backtest remains prohibited until all Phase 02 gates pass.

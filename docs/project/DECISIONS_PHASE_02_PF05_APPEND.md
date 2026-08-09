# DECISIONS.md — Phase 02B PF05 Append

## D02-PF05-01 — Earlier decisions must be invariant to future rows

**Decision:** A strategy decision produced from the full supplied panel must equal the decision produced after truncating the panel at that decision date across features, universe, ranking, candidates, targets, and exits.

## D02-PF05-02 — Recursive stability is mandatory after approved warm-up

**Decision:** Once at least 300 sessions are supplied, the same historical decision must remain stable under the frozen 300/320/360-session recursive validation windows.

## D02-PF05-03 — Validation compares decision semantics, not absolute history count

**Decision:** `valid_session_count` is excluded from recursive snapshot hashing because its absolute value changes by construction when the start of history changes. Its decision effect remains tested through eligibility.

## D02-PF05-04 — Validation canonicalization uses 10 decimal places

**Decision:** PF05 rounds floating-point comparison output to 10 decimal places before hashing to avoid false failures from machine-level rolling arithmetic. Strategy calculations themselves are unchanged.

## D02-PF05-05 — Contaminated controls are required evidence

**Decision:** PF05 cannot pass based solely on clean fixtures. Deliberately future-dependent and recursive-unstable fixtures must fail for the validator to be accepted.

## D02-PF05-06 — Source-level PIT controls remain authoritative

**Decision:** PF05 detects algorithmic dependence on future rows. It does not replace `available_at <= decision_at`, revision, manifest, universe, or provider point-in-time controls.

## D02-PF05-07 — Exit validation is extensible

**Decision:** PF05 accepts an injected deterministic exit evaluator so future PF07 holding/exit logic can be validated without modifying the core validator.

## D02-PF05-08 — PF05 PASS does not authorize Phase 03

**Decision:** Synthetic lookahead/recursive PASS is a pre-purchase platform gate only. Acceptance backtesting remains prohibited until all Phase 02 platform and external data gates pass.

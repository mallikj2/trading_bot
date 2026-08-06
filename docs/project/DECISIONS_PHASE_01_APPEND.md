# DECISIONS.md — Phase 01 Append

## DR-P01-001 — v0.1 specification review

- **Date:** 2026-08-05
- **Status:** CLOSED — superseded before approval
- **Decision:** Do not approve `CSMOM-LS-v0.1`.
- **Reason:** The draft contained unresolved deterministic rules and its passing tests were partly vacuous because the synthetic fixture selected zero candidates.
- **Performance implication:** None; the hypothesis was not rejected based on returns.
- **Replacement:** `CSMOM-LS-v0.2`.

## DR-P01-002 — First strategy research candidate v0.2

- **Date:** 2026-08-05
- **Status:** PROPOSED — awaiting explicit owner approval
- **Decision:** Adopt `CSMOM-LS-v0.2` as the first strategy research candidate.
- **Scope:** Research specification only; no paper/live order authorization.
- **Hypothesis:** Intermediate cross-sectional momentum among liquid US common equities may produce a persistent matched-gross long-short return spread over several weeks after conservative costs.
- **Primary formula:** `0.60 × robust_z(MOM12_1) + 0.40 × robust_z(MOM6_1)`.
- **Research portfolio:** Up to 3 longs and 3 shorts, matched feasible side gross, weekly entries, daily exits, 10–63 session horizon.
- **Primary fill benchmark:** Next-session 10:00–10:30 ET VWAP plus adverse costs.
- **Small-account rule:** Deterministic whole-share feasibility at USD 5,000 with maximum 10% net exposure.
- **Shorting restriction:** Research only; paper/live shorts remain prohibited until account, margin, borrow, and broker gates pass.
- **Rationale:** Simple, interpretable, aligned with swing/position horizons, laptop-compatible, and falsifiable against simple baselines.
- **Alternatives deferred/rejected:** Intraday mean reversion, fundamentals-first multifactor, and machine-learning ranking.
- **Revisit triggers:** Failed preregistered criteria, unavailable point-in-time data, impractical whole-share behavior, unsafe/unavailable shorting, or failure to beat the simple market-neutral baseline.
- **Does not modify:** Trading Mandate v0.2 or approved Phase 00 risk limits.

# DECISIONS.md — Phase 02B PF04 Append

## D02-PF04-01 — Runtime safety has three canonical states

**Decision:** The platform runtime safety states are `ACTIVE`, `REDUCING`, and `HALTED`.

## D02-PF04-02 — Safety and trading authority are separate

**Decision:** `ACTIVE` means runtime safety imposes no additional restriction; it does not authorize paper/live trading or broker mutation.

## D02-PF04-03 — Protections cannot change alpha

**Decision:** PF04 protections may restrict runtime permissions but may not change frozen CSMOM-LS-v0.2 signals, thresholds, rankings, or TradeLead factor provenance.

## D02-PF04-04 — Required protection evidence fails closed

**Decision:** Missing, unknown, expired, future-only, or ambiguous required protection evidence results in restrictive behavior rather than optimistic assumptions.

## D02-PF04-05 — Escalation is automatic; recovery is explicit

**Decision:** Runtime safety can automatically become more restrictive. It can become less restrictive only with explicit recovery approval tied to the current healthy evaluation.

## D02-PF04-06 — Most restrictive protection wins

**Decision:** The aggregate runtime state is the maximum restriction required by any registered required protection.

## D02-PF04-07 — HALTED preserves cancellation semantics

**Decision:** `HALTED` blocks exposure-changing actions while preserving cancellation semantics for future OMS integration. Broker mutation is still disabled throughout Phase 02B.

## D02-PF04-08 — Runtime safety is journaled and replayable

**Decision:** Protection evaluations and runtime transitions use PF03 event/journal infrastructure. State transitions are content-addressed and replay rejects discontinuities.

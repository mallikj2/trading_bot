# Decision log append — P02-PF10

## D-PF10-01 — Local and broker truth remain independent

Accepted. Recovery compares the PF03 journal projection with a separately captured simulated-broker snapshot. Neither source may silently overwrite the other.

## D-PF10-02 — UNKNOWN means reconcile, never resubmit

Accepted. A submission crash/timeout may represent an externally accepted order. Recovery must query/reconcile external truth and must not issue a second submit.

## D-PF10-03 — Auto-repair only uniquely evidenced broker facts

Accepted. Missed unique execution IDs and known-order state transitions may be imported. External unknown orders, missing external orders, unexplained positions, duplicate executions, ID conflicts and stale snapshots are not silently repaired.

## D-PF10-04 — Unresolved material divergence forces HALTED

Accepted. PF10 uses the PF04 reconciliation protection scope. Material unresolved findings generate incidents and require `HALTED`; de-escalation remains explicit/manual under PF04 rules.

## D-PF10-05 — PF10 is simulation evidence, not Schwab validation

Accepted. No claim is made about Schwab order behavior, reconciliation semantics, paper/live readiness, or strategy profitability. Real-broker reconciliation remains a later external validation requirement.

## D-PF10-06 — Integrated gate remains separate

Accepted. Passing PF10 completes the ten individual Phase 02B tasks but does not automatically pass `P02-PF-GATE` or authorize procurement. The integrated gate is the next task.

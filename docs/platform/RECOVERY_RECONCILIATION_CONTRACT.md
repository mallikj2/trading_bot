# PF10 Recovery + Reconciliation Contract

**Task:** P02-PF10  
**Scope:** deterministic crash/recovery simulation only  
**Live broker:** prohibited

## Purpose

PF10 proves that the platform fails closed when local immutable OMS state and external broker truth diverge. It is intentionally tested before any Schwab or commercial-provider account is purchased.

## Two independent truths

1. **Local truth** — PF03 append-only event journal projected through the PF06 OMS.
2. **External truth** — a point-in-time snapshot of the network-free `SimulatedBroker`.

Recovery compares those truths. It does not assume the local process was the last actor and it does not assume a missing acknowledgement means an order was not accepted.

## Allowed deterministic repairs

PF10 may import only uniquely evidenced facts for an already-known local order:

- broker acceptance after a crash between submission and acknowledgement;
- missed broker executions with unique execution IDs;
- a broker-evidenced terminal state on a known nonterminal order.

Every repair first moves the local order to `UNKNOWN`, then through `RECONCILING`. A submission is never repeated.

## Mismatches that are never silently repaired

- external broker order with no local immutable order history;
- local nonterminal order absent externally;
- unexplained position quantity mismatch;
- duplicate broker execution IDs;
- broker-order-ID disagreement;
- stale startup snapshot;
- local execution evidence absent from broker truth;
- interrupted recovery already left in `RECONCILING`.

These remain unresolved, create PF09 incident/audit records, and require the PF04 runtime state to be `HALTED`.

## Startup freshness

The default fixture contract accepts a broker startup snapshot only when it is at most **60 seconds old**. Future snapshots and stale snapshots fail closed.

## Duplicate-risk invariant

A crash/uncertain-order recovery path must satisfy:

`broker submission count after recovery == broker submission count before recovery`

PF10 never calls a second submit for an order that may already exist externally.

## Position reconciliation

Local position quantity is derived solely from immutable OMS execution events. Broker position quantity is taken from the captured startup snapshot. A mismatch is not corrected by inventing a fill or adjusting a position; it remains unresolved and halts the runtime.

## Incident + safety integration

Each recovery finding generates:

- `RECOVERY.FINDING` journal evidence;
- a PF09 alert/incident signal;
- and, for unresolved material divergence, a PF04 `PROTECTION.EVALUATED` plus `RUNTIME_SAFETY.TRANSITION` to `HALTED` when required.

An incident may be automatically resolved only when every finding was deterministically repaired and no unresolved divergence remains. Runtime de-escalation from an earlier `HALTED` state is never automatic.

## Explicit non-claims

PF10 does **not** prove:

- Schwab order API behavior;
- Schwab execution IDs, pagination, or startup snapshot semantics;
- broker-account position settlement behavior;
- production paper/live readiness;
- strategy profitability.

Those require later account-specific evidence and subsequent project phases.

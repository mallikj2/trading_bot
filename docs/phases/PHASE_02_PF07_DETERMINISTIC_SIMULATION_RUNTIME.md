# Phase 02B — P02-PF07 Deterministic Simulation Runtime

**Gate result:** PASS  
**Date:** 2026-08-08  
**Next task:** P02-PF08 Experiment Registry + Reporting + Attribution

## Objective

Connect the pre-purchase platform components under a single deterministic, synthetic session runtime without introducing market-data procurement, deployed paper trading, or live broker authority.

## Delivered

- deterministic content-addressed simulation plans and commands;
- controlled plan-time clock with no wall-clock decision dependency;
- PF01 TradeLead snapshot orchestration;
- PF04 protection/state-machine integration;
- PF03 append-only simulation metadata and domain event journaling;
- PF06 OMS + SimulatedBroker orchestration;
- deterministic session completion criteria;
- identical independent-run hashes;
- idempotent rerun of completed plans;
- quiescent restart/continue support;
- exact restarted-vs-uninterrupted journal-head equivalence;
- explicit rejection of restart with open/unknown orders;
- result/state hashes suitable for PF08 experiment lineage;
- CLI for local deterministic fixture plans.

## Major safety decisions

### No wall-clock trading decisions

The runtime clock advances only from the preregistered plan timestamps. Running a scenario faster/slower on the host machine cannot alter event-time decisions.

### Completion requires terminal orders

Applying all commands is not enough. A session cannot be marked complete while any OMS order remains open or uncertain.

### PF10 owns in-flight crash recovery

PF07 restart equivalence is intentionally restricted to quiescent checkpoints. If a process stops while an order is open/unknown, PF07 refuses to continue with a fresh simulated broker. This prevents the runtime from pretending broker truth survived a crash. PF10 will implement and adversarially test recovery/reconciliation.

### Runtime safety remains authoritative

Synthetic safety observations are passed through PF04. A REDUCING state blocks new simulated exposure and recovery to ACTIVE requires explicit approval.

## Acceptance evidence

The deterministic two-order fixture produces a stable plan ID, event count, journal-head hash, lead state hash, OMS state hash, and composite state hash in `PF07_SIMULATION_RUNTIME_RESULTS.json`.

An interrupted run after the first filled order, followed by journal close/reopen and continuation, produces the exact same final journal and state hashes as an uninterrupted execution of the same plan.

## Governance

PF07 does not change:

```text
PROCUREMENT_AUTHORIZED=false
PROCUREMENT_READY_FOR_MANUAL_APPROVAL=false
PHASE03_AUTHORIZED=false
```

No live broker, paid provider, or deployed paper-trading behavior is claimed.

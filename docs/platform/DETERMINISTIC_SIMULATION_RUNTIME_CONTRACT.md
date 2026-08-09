# Deterministic Simulation Runtime Contract

**Task:** P02-PF07  
**Status:** PASS candidate  
**Scope:** Synthetic/local runtime only

## Purpose

PF07 connects previously approved Phase 02B components under one controlled runtime:

```text
TradeLead snapshots
       |
       v
Deterministic session plan + clock
       |
       +--> PF04 Runtime Safety
       +--> PF03 Append-only Journal
       +--> PF06 OMS
       +--> PF06 SimulatedBroker
       |
       v
Deterministic state/result hashes
```

The runtime is designed so the same plan, timestamps, inputs, and code version produce the same event sequence, journal head, lead projection, order projection, and composite result hash.

## Common runtime boundaries

PF07 introduces explicit clock and broker capability ports. The active implementation remains deliberately constrained:

- clock source: plan timestamps only;
- broker: `SIMULATED`;
- network I/O: disabled;
- live order submission: disabled;
- deployed paper trading: not claimed.

Future paper/live runtimes may implement compatible boundaries, but they cannot be substituted during Phase 02B.

## Deterministic plan

A `SimulationPlan` is content addressed. It freezes:

- session name;
- UTC-aware start/end timestamps;
- contiguous ordered command sequence;
- exact command timestamps;
- serialized immutable input payloads.

Each `SimulationCommand` has a deterministic hash derived from ordinal, timestamp, type, and payload. Commands cannot be reordered or silently edited without changing the plan ID.

## Supported commands

- `LEAD_SNAPSHOT`
- `SAFETY_STATUS`
- `OMS_CREATE`
- `OMS_RISK_APPROVE`
- `OMS_SUBMIT`
- `OMS_FILL`
- `OMS_CANCEL`
- `OMS_EXPIRE`

PF07 does not generate alpha, alter strategy math, or fetch market/broker data.

## Clock contract

The controlled clock:

- starts at the plan start;
- may advance only to explicit plan timestamps;
- cannot move backward;
- cannot cross the plan end;
- never calls wall-clock time for trading decisions.

Clock advances are journaled as immutable `SIMULATION.CLOCK_ADVANCED` events.

## Session journal

Simulation metadata uses:

- `SIMULATION.SESSION_STARTED`
- `SIMULATION.CLOCK_ADVANCED`
- `SIMULATION.COMMAND_APPLIED`
- `SIMULATION.SESSION_COMPLETED`

Domain facts continue to use their existing authoritative PF01/PF04/PF06 event types. Simulation metadata does not replace those facts.

## Completion rule

A session is `COMPLETED` only when:

1. every plan command has been applied; and
2. every OMS order is terminal (`FILLED`, `REJECTED`, `CANCELED`, or `EXPIRED`).

An open or uncertain order can never be hidden by a completed-session marker.

## Restart equivalence

PF07 supports restart only at a **quiescent checkpoint** where all previously created orders are terminal.

At such a checkpoint:

1. close the SQLite journal;
2. reopen it in a new runtime instance;
3. replay existing PF03/PF04/PF06 facts;
4. skip already-applied commands idempotently;
5. continue remaining commands.

The final journal head and composite state hash must equal an uninterrupted run.

Restart with any open/unknown order is rejected with an explicit PF10 boundary. Broker-truth reconstruction and crash recovery of in-flight orders belongs to **P02-PF10 Recovery + Reconciliation Simulation**.

## Runtime safety integration

Synthetic protection evidence is evaluated through the real PF04 protection engine and state machine.

- degraded evidence can escalate `ACTIVE -> REDUCING`;
- failed/unknown evidence can escalate to `HALTED`;
- recovery is never automatic;
- a less restrictive state requires explicit recovery approval;
- the OMS receives the resulting runtime state and applies PF04 permissions.

Thus REDUCING blocks simulated exposure increases and HALTED blocks simulated exposure changes.

## Deterministic result

The runtime result records:

- plan ID;
- session status;
- applied/total commands;
- final controlled timestamp;
- runtime safety state;
- TradeLead projection hash;
- OMS projection hash;
- journal head hash;
- journal event count;
- composite state hash.

The result contains no assertion of strategy profitability or live readiness.

## Hard boundaries

PF07 must not:

- connect to Schwab;
- use broker/API credentials;
- use commercial market-data credentials;
- submit a real order;
- claim deployed paper trading;
- change the frozen `CSMOM-LS-v0.2` strategy;
- recover an in-flight order after process loss (PF10 scope).

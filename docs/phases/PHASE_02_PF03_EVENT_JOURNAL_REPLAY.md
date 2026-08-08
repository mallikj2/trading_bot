# Phase 02B — P02-PF03 Event Journal + Deterministic Replay

**Date:** 2026-08-08  
**Status:** PASS  
**Phase 02:** ACTIVE  
**Procurement authorized:** NO  
**Phase 03 authorized:** NO

## Objective

Add a persistent event/audit backbone before runtime safety, OMS, simulation, alerts, and recovery work. Historical platform facts must be append-only, tamper-evident, idempotent across restart, and deterministically replayable.

## Delivered

### Immutable domain events

- canonical `DomainEvent` envelope;
- content-addressed SHA-256 event identity;
- aggregate/correlation/causation metadata;
- schema version and producer metadata;
- UTC timestamp normalization;
- canonical JSON serialization;
- rejection of native float payload values.

### Append-only persistent journal

- SQLite-backed journal using only Python standard library;
- monotonic journal sequence;
- storage-level UPDATE/DELETE prohibition triggers;
- SHA-256 hash chain;
- idempotent duplicate append;
- prior-causation validation;
- correlation continuity checks;
- aggregate/correlation query filters;
- deterministic JSONL export;
- restart/reopen integrity validation.

### Deterministic replay

- generic projector protocol;
- canonical state hashing;
- replay through an explicit historical sequence;
- `TradeLeadProjector` integrating PF01 lifecycle/conflict rules;
- `TRADE_LEAD.SNAPSHOT` event factory;
- replay CLI for journal verification and state reconstruction.

## Key governance decisions

1. A journal entry is never corrected in place. Corrections are later events.
2. `recorded_at` is storage metadata and does not alter the domain event's deterministic identity.
3. Replay order is journal sequence; occurrence time remains domain evidence but cannot reorder persisted causality.
4. Causation can only reference an earlier journaled event and retains the same correlation ID.
5. Lead replay reuses PF01 `TradeLeadBook`; PF03 does not create a second lifecycle rule set.
6. Runtime state/OMS/reconciliation event schemas remain owned by PF04/PF06/PF10 rather than being invented prematurely.

## Acceptance evidence

PF03 tests prove:

- stable event IDs under JSON key reordering;
- float rejection and UTC normalization;
- idempotent duplicate ingestion;
- missing/invalid causation rejection;
- append-only SQLite trigger enforcement;
- offline tamper detection;
- persistent hash continuity after reopen;
- deterministic JSONL export;
- deterministic lead state hash across repeated replay;
- historical replay through an earlier journal sequence;
- divergent TradeLead lifecycle branch rejection;
- restart/reopen replay equivalence using PF01 fixture leads.

## Out of scope

- ACTIVE/REDUCING/HALTED runtime state — PF04;
- lookahead/recursive validation — PF05;
- OMS/SimulatedBroker — PF06;
- deterministic simulation runtime — PF07;
- experiment registry — PF08;
- incident center — PF09;
- broker recovery/reconciliation — PF10;
- commercial data/provider credentials;
- real broker/order mutation.

## Gate result

**P02-PF03 = PASS**

`P02-PF-GATE` remains blocked because PF04–PF10 remain incomplete.

**Next task: P02-PF04 — Runtime Safety State + Protections.**

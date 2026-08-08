# Phase 02B — P02-PF01 TradeLead + Watchlist Domain Model

**Date:** 2026-08-08  
**Status:** PASS  
**Phase 02:** ACTIVE  
**Procurement authorized:** NO  
**Phase 03 authorized:** NO

## Objective

Create the canonical deterministic object that carries a strategy/research opportunity into later portfolio construction, risk evaluation, read-only UI, audit, simulation, OMS, and eventual execution planning.

## Delivered

- immutable deterministic `TradeLead` identity;
- stable LONG/SHORT direction and strategy/version identity;
- historical decision symbol separated from current/display alias;
- score plus named factor observations;
- trend, volatility, universe, earnings, cost, and borrow state;
- required dataset/universe/feature SHA-256 provenance;
- factor/provenance availability-time checks;
- explicit lifecycle state machine and transition history;
- structured deterministic rejection/block reason codes;
- deterministic Watchlist projection with "what prevents qualification" actions;
- once-only proposed portfolio allocation;
- deterministic JSON serialization/content hashes;
- idempotent lead registry with stale/duplicate handling and conflict detection;
- no broker/network/order side effects.

## Governance decisions

1. Signal score/factor values are frozen at the decision timestamp.
2. WATCHLIST and blocked/rejected decision artifacts do not requalify later by rewriting themselves. A later strategy decision creates a new lead.
3. Later operational blocks may advance a previously qualified/planned lead to a blocked/rejected state without modifying the frozen signal.
4. Current/display ticker changes are presentation-only; historical decision symbol remains immutable.
5. `PLANNED` and later entered-position states require a concrete proposed whole-share allocation.
6. Watchlist explanations come from structured reason codes, not post-hoc AI-generated rationales.

## Acceptance evidence

PF01 acceptance requirements are satisfied by focused tests covering:

- deterministic lead ID;
- deterministic factor/provenance ordering;
- lifecycle transition validity;
- blocked-state reason categories;
- signal immutability through later rejection/exit states;
- point-in-time future-data rejection;
- serialization round-trip;
- duplicate/idempotency behavior;
- conflicting same-ID rejection;
- allocation immutability;
- watchlist action derivation;
- absence of order-submission surface.

The full cumulative regression must also remain clean before the repository bundle is promoted.

## Out of scope

- FastAPI/React UI — PF02;
- persistent event journal/replay — PF03;
- operational runtime safety state — PF04;
- lookahead/recursive validation — PF05;
- OMS/SimulatedBroker — PF06;
- deployed paper/live trading;
- provider procurement or credentials.

## Gate result

**P02-PF01 = PASS**

`P02-PF-GATE` remains not ready because PF02–PF10 are not yet complete.

Procurement remains deferred.

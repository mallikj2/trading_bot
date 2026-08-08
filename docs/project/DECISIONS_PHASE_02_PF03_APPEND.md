# DECISIONS.md — Phase 02B PF03 Append

## D02-PF03-01 — Domain events are content-addressed

**Decision:** `event_id` is the SHA-256 of a canonical immutable domain-event body. Storage ingestion time is excluded from domain identity.

**Rationale:** The same domain fact can be safely retried after restart without creating duplicate business events.

## D02-PF03-02 — Journal history is append-only and tamper-evident

**Decision:** SQLite UPDATE/DELETE triggers prohibit ordinary mutation and every record participates in a SHA-256 journal hash chain.

**Rationale:** Runtime/audit facts must not be silently rewritten. Hash verification also detects direct/offline modifications that bypass application controls.

## D02-PF03-03 — Corrections are new events

**Decision:** A historical event is never edited. A correction/reversal must be represented as a later versioned domain event owned by the relevant domain task.

## D02-PF03-04 — Replay follows journal sequence

**Decision:** Deterministic replay consumes strictly increasing persisted journal sequence. `occurred_at` is preserved as domain evidence but does not override persisted causal order.

## D02-PF03-05 — Causation is backward-only with correlation continuity

**Decision:** `causation_id` must reference an already persisted event and the child must retain the same `correlation_id`.

## D02-PF03-06 — Projection state is hashed canonically

**Decision:** Every deterministic replay result exposes a SHA-256 hash of the projector's canonical JSON snapshot.

## D02-PF03-07 — PF01 remains authoritative for TradeLead history

**Decision:** `TradeLeadProjector` reuses `TradeLeadBook` ingestion/conflict semantics instead of duplicating lead lifecycle rules in the event subsystem.

## D02-PF03-08 — Event schemas are introduced by owning domains

**Decision:** PF03 defines generic event infrastructure and the TradeLead snapshot event only. Risk-state, OMS, incident, and reconciliation event types are deferred to PF04/PF06/PF09/PF10.

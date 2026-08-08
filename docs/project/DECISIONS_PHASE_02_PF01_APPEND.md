# DECISIONS.md — Phase 02B PF01 Append

## D02-PF01-01 — Canonical TradeLead research artifact

**Decision:** Adopt `TradeLead` as the canonical object passed from strategy/research into later portfolio, risk, UI, audit, simulation, OMS, and execution-planning layers.

**Rationale:** A stable domain boundary prevents UI/execution code from reconstructing or inventing strategy rationale.

## D02-PF01-02 — Freeze decision-time alpha evidence

**Decision:** Strategy score, factors, decision symbol, strategy version, and data/universe/feature provenance are immutable within a lead.

**Rationale:** Later operational information must not retroactively rewrite the research decision.

## D02-PF01-03 — New decision creates new qualification artifact

**Decision:** WATCHLIST and blocked/rejected decision artifacts cannot later transition back to QUALIFIED. If a later decision cycle satisfies the strategy conditions, it creates a new lead.

**Rationale:** This prevents future market information from changing the meaning of an earlier decision-time artifact.

## D02-PF01-04 — Structured reasons are authoritative

**Decision:** Watchlist/rejection explanations must originate from deterministic reason codes/details recorded by the system. AI-generated prose may later summarize those reasons but cannot become the authoritative reason source.

## D02-PF01-05 — Current ticker is presentation-only

**Decision:** The historical decision symbol is frozen. A current/display symbol can change monotonically for presentation without changing lead identity or the historical decision record.

## D02-PF01-06 — No execution authority in PF01

**Decision:** PF01 contains no order submission, cancellation, broker connectivity, network I/O, or secret handling.

**Effect:** Procurement and Phase 03/live authority remain unchanged.

# Decision Log Append — P02-PF06

## D02-PF06-01 — Order intent is immutable and source-lead-addressed

Accepted. Orders retain the source TradeLead ID/content hash, strategy/version, stable instrument identity, direction-derived side, whole-share quantity, and decision provenance.

## D02-PF06-02 — UNKNOWN orders may never be blindly resubmitted

Accepted. Any uncertain submission/cancellation enters `UNKNOWN` and must enter `RECONCILING` before a broker-confirmed state can be restored.

## D02-PF06-03 — Journal order facts before projection

Accepted. PF03 domain events are the authoritative lifecycle facts. In-memory order state is a replayable projection.

## D02-PF06-04 — PF04 runtime safety governs simulated exposure

Accepted. ACTIVE allows simulated increase/reduction, REDUCING permits reduction only, and HALTED permits cancellation but no exposure change.

## D02-PF06-05 — Simulated broker only in Phase 02B

Accepted. PF06 contains no Schwab connection, network I/O, authentication, broker credentials, or live mutation surface. Deployed paper/live trading claims remain prohibited.

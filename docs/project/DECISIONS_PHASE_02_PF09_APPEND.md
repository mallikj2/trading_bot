# DECISIONS append — P02-PF09

## D-P02-PF09-01 — Journal-backed alerts are authoritative

**Decision:** Alerts/incidents are reconstructed from immutable PF03 events rather than mutable UI records.

**Rationale:** supports auditability, restart/replay and tamper detection.

## D-P02-PF09-02 — Stable fingerprint deduplication

**Decision:** rule/component/entity/condition/incident-key form the active deduplication fingerprint. Exact signal re-ingestion is a no-op; later same-fingerprint evidence increments the active alert rather than creating alert spam.

## D-P02-PF09-03 — Severity is monotonic while active

**Decision:** active alerts may escalate but not de-escalate. Lower-severity later evidence cannot hide an existing critical condition.

## D-P02-PF09-04 — Acknowledgement is invalidated by materially new evidence

**Decision:** a new related alert or severity escalation after acknowledgement reopens the incident and clears the previous acknowledgement. Same-severity duplicate evidence alone does not reopen it.

## D-P02-PF09-05 — No automatic incident resolution

**Decision:** incident resolution requires an explicit actor/resolution and emits immutable alert-closure plus incident-resolution events.

## D-P02-PF09-06 — Local console only before procurement

**Decision:** PF09 depends on no paid notification provider. Outbound email/SMS/chat/push integrations are deferred; external credentials are prohibited in Phase 02B.

## D-P02-PF09-07 — Incident severity does not grant trading authority

**Decision:** PF09 observes operational state. PF04 remains authoritative for runtime trading restrictions, and Phase 02 governance continues to prohibit live broker mutation.

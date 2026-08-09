# Alert + Incident Center Contract — P02-PF09

**Status:** PASS  
**Phase:** 02B Pre-Purchase Platform Foundation  
**Scope:** Local deterministic operational observability only.

## Purpose

PF09 converts operational/research conditions into immutable, journal-backed alert and incident facts. It provides visibility and lifecycle control without introducing live-order authority, strategy mutation, or paid notification dependencies.

## Alert identity and deduplication

`AlertSignal` is immutable and content-addressed. A stable fingerprint is derived from:

- `rule_id`
- `component`
- `entity_id`
- `condition_key`
- `incident_key`

The signal ID additionally binds severity, occurrence time, title/detail and evidence hash.

Rules:

1. Exact re-ingestion of an already processed signal is a no-op.
2. A later observation with the same fingerprint is deduplicated into the active alert.
3. Severity may escalate `INFO -> WARNING -> CRITICAL` but never de-escalates while the alert remains active.
4. A resolved condition observed again opens a new incident generation; old history is not rewritten.

## Incident grouping

The default incident key is `component:entity_id`. Multiple rules for the same active operational subject can therefore group into one incident while retaining separate alert identities.

Incident lifecycle:

`OPEN -> ACKNOWLEDGED -> RESOLVED`

A new related alert or severity escalation after acknowledgement emits `INCIDENT.REOPENED`; acknowledgement metadata is cleared and fresh human acknowledgement is required.

Resolution closes all active alerts in the incident through explicit `ALERT.RESOLVED` events before the terminal `INCIDENT.RESOLVED` event.

## Journal facts

PF09 uses the PF03 append-only SQLite event journal. Supported event types are:

- `INCIDENT.OPENED`
- `ALERT.RAISED`
- `ALERT.DEDUPLICATED`
- `ALERT.ESCALATED`
- `INCIDENT.ACKNOWLEDGED`
- `INCIDENT.REOPENED`
- `ALERT.RESOLVED`
- `INCIDENT.RESOLVED`

Restart/replay must reproduce the identical incident/alert projection and journal head hash.

## Severity semantics

- `INFO`: informational operational condition.
- `WARNING`: degraded condition requiring attention.
- `CRITICAL`: severe operational/research integrity condition.

PF09 severity is observability metadata. It does not itself authorize orders. Runtime trading restrictions remain the responsibility of PF04 protection/risk state.

## Read-only UI boundary

The Research Console exposes:

`GET /api/v1/incidents`

No acknowledgement/resolution mutation endpoint exists in Phase 02. PF09 lifecycle commands are internal deterministic services used by tests/simulation and later operational tooling only after governance approval.

## Notification boundary

PF09 requires no paid notification service. The only enabled delivery channel in Phase 02B is:

`LOCAL_RESEARCH_CONSOLE`

Email, SMS, Slack, Telegram, push or paging integrations are intentionally outside PF09 acceptance and require later explicit configuration/security review.

## Hard boundaries

PF09 MUST NOT:

- submit/cancel live broker orders;
- alter CSMOM-LS-v0.2 signal logic;
- store broker or commercial-data credentials;
- require a paid notification provider;
- silently resolve incidents;
- overwrite historical alert/incident events.

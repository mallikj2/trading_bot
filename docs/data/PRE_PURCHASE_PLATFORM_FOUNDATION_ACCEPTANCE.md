# Pre-Purchase Platform Foundation — Acceptance Matrix

**Phase:** Phase 02B  
**Purpose:** Complete/test internal platform capabilities before commercial data/broker procurement.

| ID | Capability | Mandatory evidence | Must not do |
|---|---|---|---|
| P02-PF01 | TradeLead + Watchlist | deterministic lifecycle, provenance, reason codes, serialization/idempotency tests | submit orders |
| P02-PF02 | Read-only API + React UI | OpenAPI + frontend tests, fixture integration, no mutation routes | expose secrets or trade commands |
| P02-PF03 | Event journal/replay | append-only journal, deterministic replay/state hash | mutate historical events |
| P02-PF04 | Runtime safety/protections | ACTIVE/REDUCING/HALTED transition tests | silently change alpha rules |
| P02-PF05 | Lookahead/recursive validation | clean fixtures pass; contaminated fixtures fail | accept future-data differences |
| P02-PF06 | OMS + SimulatedBroker | full lifecycle, partial fill/reject/cancel/UNKNOWN tests | connect to Schwab/live broker |
| P02-PF07 | Deterministic simulation runtime | common runtime interfaces, clock/order determinism, restart equivalence | claim deployed paper/live readiness |
| P02-PF08 | Experiment/reporting | immutable registry, result hashes, fixture reports/attribution | claim strategy profitability |
| P02-PF09 | Alerts/incidents | dedup/escalation/ack/resolution + UI | depend on paid notification service |
| P02-PF10 | Recovery/reconciliation simulation | adversarial recovery without duplicate risk | reconcile against real broker |

## Integrated PASS requirements

`P02-PF-GATE = PASS` only when all ten tasks pass and an end-to-end synthetic session demonstrates:

- deterministic lead generation;
- read-only UI visibility;
- explicit watchlist/rejection reasons;
- risk/OMS/simulated fill flow;
- event journal completeness;
- deterministic replay;
- runtime-state enforcement;
- recovery/reconciliation safety;
- experiment/reporting lineage;
- zero live broker mutation paths;
- zero embedded commercial credentials.

## Procurement state

Before integrated PASS:

```text
PROCUREMENT_AUTHORIZED=false
PROCUREMENT_READY_FOR_MANUAL_APPROVAL=false
```

After integrated PASS:

```text
PROCUREMENT_AUTHORIZED=false
PROCUREMENT_READY_FOR_MANUAL_APPROVAL=true
```

Actual purchases still require an explicit user/governance decision.

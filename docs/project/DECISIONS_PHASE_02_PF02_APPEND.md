# DECISIONS.md — Phase 02B PF02 Append

## D02-PF02-01 — API is read-only by construction

**Decision:** Phase 02B Research Console exposes GET-only resources and validates its generated OpenAPI surface against an explicit read-only method allowlist.

**Rationale:** UI visibility must not create accidental trading authority.

## D02-PF02-02 — Strategy logic remains server-side

**Decision:** React may sort/filter/display authoritative lead fields but cannot calculate CSMOM-LS factors, scores, eligibility, risk decisions, or lifecycle transitions.

## D02-PF02-03 — Fixture state must be unmistakable

**Decision:** Synthetic Portfolio/Risk/provider state must be explicitly labeled as fixture/research data and never visually presented as a live broker account.

## D02-PF02-04 — No browser credential storage

**Decision:** The Phase 02 frontend stores no broker/provider API keys, tokens, passwords, or session credentials in browser storage.

## D02-PF02-05 — Governance is visible but non-mutable

**Decision:** Phase Gates and Data Health are exposed in the UI for inspection only. Gate promotion remains an evidence-backed backend/governance process.

## D02-PF02-06 — Event persistence is deferred to PF03

**Decision:** PF02 audit data is a deterministic read projection over fixture lead provenance. Persistent append-only journaling and replay are owned by PF03.

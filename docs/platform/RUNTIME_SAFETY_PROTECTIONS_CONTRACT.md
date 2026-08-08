# Runtime Safety State + Protections Contract

**Task:** P02-PF04  
**Status:** PASS candidate  
**Scope:** Phase 02B pre-purchase platform foundation

## 1. Purpose

Provide a deterministic operational safety layer that can restrict runtime behavior independently of strategy alpha. This layer does **not** alter the frozen `CSMOM-LS-v0.2` signal, universe, ranking, sizing, or exit rules.

## 2. Runtime states

| State | Simulated new exposure | Risk reduction | Cancel semantics | Live broker mutation |
|---|---:|---:|---:|---:|
| `ACTIVE` | allowed by runtime safety | allowed | allowed | prohibited in Phase 02 |
| `REDUCING` | blocked | allowed | allowed | prohibited in Phase 02 |
| `HALTED` | blocked | blocked | allowed | prohibited in Phase 02 |

These are **runtime safety permissions**, not trading authority. Phase 02 governance separately prohibits deployed paper/live order submission even when runtime safety is `ACTIVE`.

## 3. Protection evidence

Every required protection receives a point-in-time `ProtectionObservation` containing:

- protection ID and scope;
- health status;
- `observed_at`;
- `available_at`;
- `expires_at`;
- deterministic reason/detail;
- source evidence SHA-256.

Future evidence cannot be used. Missing, unknown, expired, or conflicting evidence fails closed.

## 4. Built-in rule families

### Status rule

- `HEALTHY -> ACTIVE`
- `DEGRADED -> REDUCING`
- `FAILED -> HALTED`
- `UNKNOWN -> HALTED`
- missing/expired -> `HALTED`

### Staleness rule

Operational freshness can independently map age bands to `ACTIVE`, `REDUCING`, or `HALTED`. It operates on source freshness only; it must never be used to change alpha thresholds.

## 5. Aggregation

The protection engine evaluates the fixed required protection set and chooses the **most restrictive** state. Unknown/unregistered protection evidence is rejected rather than silently ignored.

Same-availability conflicting records for a protection are an ambiguity error.

## 6. Transition policy

- Escalation is automatic and deterministic.
- Same-state evaluation is idempotent.
- Recovery/de-escalation is never automatic.
- Recovery requires explicit `RecoveryApproval` acknowledging the current healthy evaluation.
- A recovery approval cannot target a state different from the currently evaluated safe state.

## 7. Journal/replay

PF04 adds:

- `PROTECTION.EVALUATED`
- `RUNTIME_SAFETY.TRANSITION`

Transition events are causally linked to their evaluation event and replay through `RUNTIME_SAFETY_V1`. Transition IDs are content-addressed and replay rejects state discontinuities or tampered IDs.

## 8. Initial required Phase 02 fixture protections

- `JOURNAL_INTEGRITY`
- `CONFIG_INTEGRITY`
- `RESEARCH_DATA_FRESHNESS`

Broker/reconciliation protections are defined as future scopes but are not falsely marked healthy before PF06/PF10 and real broker validation.

## 9. Hard boundaries

PF04 may **not**:

- modify `TradeLead.score` or factors;
- change momentum/trend thresholds;
- introduce a new alpha filter silently;
- submit/cancel broker orders;
- authorize paper/live trading;
- store broker/data credentials;
- make the React UI a state-mutation authority.

## 10. Acceptance

PASS requires tests proving:

- `ACTIVE / REDUCING / HALTED` mappings;
- most-restrictive aggregation;
- future/missing/stale evidence fail closed;
- automatic escalation;
- explicit-only recovery;
- state permission enforcement;
- journal/replay determinism;
- read-only UI exposure;
- zero strategy-alpha mutation surface.

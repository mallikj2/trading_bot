# Phase 6 — Order and Broker Safety

## Status

**NOT STARTED — blocked by earlier phases.**

## Objective

Specify a deterministic, idempotent, reconciliation-aware order lifecycle with broker state as the authority.

## Required order states

`CREATED`, `RISK_APPROVED`, `SUBMISSION_PENDING`, `SUBMITTED`, `ACKNOWLEDGED`, `PARTIALLY_FILLED`, `FILLED`, `CANCEL_PENDING`, `CANCELED`, `REPLACE_PENDING`, `REJECTED`, `EXPIRED`, `UNKNOWN`, and `MANUAL_REVIEW`.

## Required controls

- Deterministic client order identifiers
- Local and broker duplicate checks before submission
- Startup and periodic reconciliation
- Unknown state blocks new risk
- Partial-fill and reject handling
- Controlled cancel/replace behavior
- Spread and volume-participation constraints
- Authoritative calendar, holidays, early closes, DST, and halt handling

## Exit gate

Retries must not duplicate exposure, timeouts must not imply fills, and unresolved reconciliation must fail closed.

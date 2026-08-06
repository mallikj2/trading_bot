# Phase 7 — Reliability and Operations

## Status

**NOT STARTED — blocked by earlier phases.**

## Objective

Make the system safe through startup validation, durable recovery, monitoring, and independently testable kill controls.

## Startup preflight

Verify environment, account, strategy version, clock, market status, data freshness, broker connectivity, buying power, positions, open orders, risk limits, database health, disk space, secrets, alert channel, and kill-switch operation.

## Restart recovery

Enter non-trading recovery, restore durable state, query broker state, reconcile, expire stale signals, recalculate risk, require manual review for unresolved differences, and resume only after all checks pass.

## Required controls

- Software and manual kill switches
- Cancel-all-open-orders action
- Exit-only mode
- Explicitly governed flatten procedure
- Alerts for orders, fills, rejects, risk breaches, stale data, disconnects, mismatches, unexpected positions, loss thresholds, halts, and restarts

## Exit gate

Alert failure must not make the system unsafe. Crash, sleep, network, broker, persistence, and stale-data scenarios must have evidence-backed recovery behavior.

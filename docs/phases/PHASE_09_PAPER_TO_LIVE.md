# Phase 9 — Paper-to-Live Progression

## Status

**NOT STARTED — all prior phases are prerequisites.**

## Objective

Use paper trading to test integration and operations, then permit only tightly capped live exposure after explicit evidence-based approval.

## Paper requirements

- Historical gates passed
- Final out-of-sample data remained protected
- Conservative costs and execution assumptions documented
- Paper behavior matched intended deterministic rules
- Restart, reconciliation, duplicate-order, rejection, staleness, kill-switch, and recovery tests passed
- No unresolved critical defects
- Minimum number of sufficiently independent decisions reached

## Initial limited-live requirements

- No leverage unless separately approved
- Long-only unless shorting separately passed
- One-share or tightly capped capital
- Small maximum total exposure
- Manual daily arming
- Strict daily loss limit
- No automatic capital scaling

## Exit gate

Capital scaling requires a new decision after actual fills, slippage, risk behavior, and recovery behavior remain within documented tolerances relative to simulation and paper trading.

## Current result

**FAIL — the project is not eligible for paper or live trading.**

# Phase 4 — Risk-Management Specification

## Status

**NOT STARTED — blocked by earlier phases.**

## Objective

Specify and test an independent deterministic risk engine with authority to reduce or reject every proposed order.

## Required outputs

- Position-sizing formula and invalid-input behavior
- Single-name, sector, industry, correlation, gross, net, overnight, open-order, illiquid, daily-loss, weekly-loss, and drawdown limits
- Stop and exit hierarchy
- Predefined scaling rules with total-risk caps
- Risk state machine and deterministic transitions
- Stress scenarios and gap-risk treatment

## Key failure modes

- Strategy bypass of risk controls
- Hidden fallback sizing on calculation failure
- Full Kelly or unstable estimates
- Correlation treated as independent positions
- Uncontrolled averaging down
- Assuming stops guarantee execution price

## Exit gate

All thresholds, state transitions, reason codes, and rejection behavior must be testable and approved.

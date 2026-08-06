# Acceptance Criteria Register

Acceptance criteria must be recorded before protected evaluation. Criteria may not be weakened after observing final out-of-sample or live results.

## Phase 0 — Mandate Discovery

### Required evidence

- Twelve critical mandate decisions answered
- Feasibility conflicts documented
- Three candidate mandates compared against actual constraints
- One mandate explicitly approved
- Initial risk tolerances and operating constraints recorded

### Exit decision

Current status: **CONDITIONAL PASS — incomplete**

## Phase 1 — Strategy Research Specification

Status: **NOT REGISTERED**

Before protected evaluation, register minimum acceptable values or explicit comparison rules for:

- Net return after costs
- Sharpe and/or Sortino ratio
- Maximum drawdown
- Calmar ratio
- Turnover
- Average trade expectancy
- Profit factor
- Tail loss
- Stability across time periods
- Stability across nearby parameters
- Performance versus relevant baselines

## Phase 2 — Data and Statistical Design

Status: **NOT REGISTERED**

Required categories include point-in-time coverage, corporate actions, universe reconstruction, null policy, timestamp semantics, immutable raw storage, feature versioning, unit tests, and leakage tests.

## Phase 3 — Backtesting and Falsification

Status: **NOT REGISTERED**

Required categories include walk-forward design, protected final out-of-sample data, multiple-testing history, cost scenarios, conservative fill rules, confidence intervals, regime tests, ablations, and parameter stability.

## Phase 4 — Risk Management

Status: **NOT REGISTERED**

Required categories include deterministic position sizing, portfolio limits, state transitions, stress constraints, invalid-input rejection, and independent risk authority.

## Phase 5 — Production Architecture

Status: **NOT REGISTERED**

Required categories include typed boundaries, environment separation, durable state, UTC timestamps, secret isolation, modular adapters, migration strategy, and test layers.

## Phase 6 — Order and Broker Safety

Status: **NOT REGISTERED**

Required categories include order state machine, idempotency, broker reconciliation, unknown-state handling, partial fills, reject and cancel behavior, and market calendar controls.

## Phase 7 — Reliability and Operations

Status: **NOT REGISTERED**

Required categories include startup preflight, crash recovery, connection recovery, stale-signal expiry, kill switches, disk/database checks, and alert-failure safety.

## Phase 8 — Journal and Governance

Status: **NOT REGISTERED**

Required categories include complete decision lineage, versioned inputs, human override records, expected-versus-realized execution, and reproducible periodic reports.

## Phase 9 — Paper-to-Live

Status: **NOT REGISTERED**

See `docs/governance/PAPER_TO_LIVE_GATES.md`.

## Change control

After criteria are frozen, changes are allowed only for objectively demonstrated data or implementation defects. Every change requires:

1. A decision record
2. The defect and impact
3. The old and new criterion
4. A new protected evaluation plan
5. Confirmation that prior protected results will not be reused as untouched evidence

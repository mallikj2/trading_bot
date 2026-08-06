# CURRENT_STATE.md — Phase 01 Patch

Merge this state into the canonical project-state document without deleting Phase 00 history or approved risk limits.

```yaml
project:
  current_phase: PHASE_01_STRATEGY_RESEARCH_SPECIFICATION
  phase_status: CONDITIONAL_PASS_AWAITING_OWNER_APPROVAL

  phase_00:
    status: PASS
    approved_mandate_version: "0.2"

  phase_01:
    prior_candidate:
      id: CSMOM-LS-v0.1
      status: SUPERSEDED_BEFORE_APPROVAL
      reason: INCOMPLETE_SPECIFICATION_AND_VACUOUS_TESTS
    active_candidate:
      id: CSMOM-LS-v0.2
      status: PROPOSED
      approval_status: PENDING
      focused_tests:
        status: PASS
        count: 18
        evidence_file: TEST_RESULTS.md

  live_capital_reference_usd: 5000
  preferred_live_broker: Schwab
  account_type: UNDECIDED
  live_shorting_status: PROHIBITED_PENDING_ACCOUNT_BORROW_AND_BROKER_VALIDATION
  live_trading_status: NOT_AUTHORIZED

  next_phase:
    id: PHASE_02_DATA_AND_STATISTICAL_DESIGN
    formal_entry_condition: APPROVE_STRATEGY_SPEC_V0_2

  blockers:
    - Explicit owner approval of CSMOM-LS-v0.2

  unresolved_nonblocking_for_phase_02_design:
    - Final account type
    - Schwab paper/live short capability and borrow workflow
    - Production and historical data vendors
    - Availability and limits of point-in-time earnings and borrow data
```

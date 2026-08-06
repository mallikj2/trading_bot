# CURRENT_STATE.md — Phase 02 Reconciliation Patch

Merge this state into the canonical current-state document without deleting Phase 00/01 history or changing approved mandate and strategy thresholds.

```yaml
project:
  snapshot_date: "2026-08-05"
  current_phase: PHASE_02_DATA_AND_POINT_IN_TIME_DESIGN
  overall_status: ACTIVE_DATA_CONTRACT_VALIDATION

  phase_00:
    status: PASS
    approved_mandate_version: "0.2"

  phase_01:
    status: PASS
    approved_strategy:
      id: CSMOM-LS-v0.2
      version: "0.2"
      approval_phrase: APPROVE_STRATEGY_SPEC V0.2
      approval_date: "2026-08-05"
    prior_candidate:
      id: CSMOM-LS-v0.1
      status: SUPERSEDED_BEFORE_APPROVAL
    focused_tests:
      status: PASS
      count: 19
      revalidated_date: "2026-08-05"

  phase_02:
    status: ACTIVE
    phase_01_reconciliation:
      status: PASS
      contract_id: CSMOM-LS-v0.2-DATA-v0.1
    active_task: RESEARCH_PROVIDER_PROOF_OF_CONCEPT

  strategy_research:
    direction: LONG_AND_SHORT
    live_shorting_status: PROHIBITED_PENDING_LATER_GATES
    live_trading_status: NOT_AUTHORIZED
    paper_order_status: NOT_AUTHORIZED

  data_requirements:
    tradable_universe: NYSE_AND_NASDAQ_COMMON_STOCKS
    reference_instrument: SPY_NON_TRADABLE
    universe_refresh: MONTHLY
    weekly_entry_review: FIRST_ELIGIBLE_SESSION
    daily_exit_review: true
    final_fill_benchmark: NEXT_SESSION_10_00_TO_10_30_ET_VWAP
    minimum_intraday_granularity: FIVE_MINUTES_OR_FINER

  blockers_for_phase_02_pass:
    - Point-in-time market-cap source or validated derivation
    - Point-in-time sector taxonomy and history
    - Revision-aware historical earnings schedules
    - Validated intraday VWAP coverage
    - Frozen historical spread method
    - Survivorship-aware security master and corporate actions
    - Conservative historical short-borrow treatment

  next_phase:
    id: PHASE_03_BACKTESTING_AND_FALSIFICATION
    status: NOT_AUTHORIZED
    entry_condition: PHASE_02_PASS_AND_IMMUTABLE_EXPERIMENT_REGISTRY
```

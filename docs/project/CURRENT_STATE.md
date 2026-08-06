# Current Project State

> **Snapshot date:** 2026-08-05  
> **Project:** Professional Local Algorithmic Trading System  
> **Mandate:** v0.2 — APPROVED and LOCKED  
> **Latest approved decision:** DR-0004  
> **Completed phase:** 00 — Mandate Discovery  
> **Active phase:** 01 — Strategy Research Specification  
> **Overall status:** ACTIVE — specification only

## 1. Executive State

Phase 00 has passed. The project has an approved staged mandate: research may evaluate long and short strategies, while the initial limited-live stage is long-only, unleveraged, and requires a minimum funded capital of USD 5,000 with Charles Schwab as the provisional live broker candidate.

No strategy edge, backtest result, broker capability, or implementation result has been established. Phase 01 must define one falsifiable strategy specification and pre-register its rejection criteria before implementation or backtesting begins.

## 2. Source-of-Authority Order

When project documents conflict, use the following order and stop for explicit resolution rather than silently selecting a value:

1. Master governing specification.
2. `docs/governance/TRADING_MANDATE.md`.
3. Approved entries in `docs/project/DECISIONS.md`.
4. The latest accepted phase document.
5. `docs/project/CURRENT_STATE.md` as the operational snapshot.

`CURRENT_STATE.md` summarizes approved state; it does not independently amend the mandate.

## 3. Phase Status

| Phase | Name | Status | Authorization |
|---:|---|---|---|
| 00 | Mandate Discovery | PASS | Complete |
| 01 | Strategy Research Specification | ACTIVE | Specification work authorized |
| 02 | Data and Statistical Design | NOT STARTED | Not authorized |
| 03 | Backtesting and Falsification | NOT STARTED | Not authorized |
| 04 | Risk-Management Specification | NOT STARTED | Not authorized |
| 05 | Production Architecture | NOT STARTED | Not authorized |
| 06 | Execution and Broker Integration | NOT STARTED | Not authorized |
| 07 | Reliability and Operations | NOT STARTED | Not authorized |
| 08 | Journal, Analytics, and Governance | NOT STARTED | Not authorized |
| 09 | Paper-to-Live Gates | NOT STARTED | Not authorized |
| 10 | Controlled Scaling and Ongoing Validation | NOT STARTED | Not authorized |

Phases must proceed sequentially. Future-phase implementation must not be introduced early merely because it is convenient.

## 4. Locked Mandate Snapshot

| Item | Current approved state |
|---|---|
| Live-capital target | Minimum USD 5,000 |
| Research direction | Long and short |
| Initial limited-live direction | Long-only |
| Horizon | Swing and position |
| Frequency | Daily/end-of-day or otherwise low-frequency |
| Intraday | Excluded initially |
| Overnight/weekend | Permitted subject to explicit risk and event rules |
| Live broker candidate | Charles Schwab |
| Paper broker candidate | Moomoo |
| Account operating mode | No borrowed cash and no leverage during initial live |
| Initial live shorting | Disabled |
| Initial monthly data budget | USD 80 ceiling |
| Human approval | Daily arming plus per-order Telegram approval |
| Host environment | Local Windows 11 laptop |

## 5. Locked Initial Risk Limits

| Risk control | Limit |
|---|---:|
| Planned risk per position | 0.50% of equity |
| Aggregate open planned risk | 2.00% of equity |
| Daily loss threshold | 1.00% of start-of-day equity |
| Weekly loss threshold | 3.00% of week-start equity |
| Drawdown warning | 6.00% peak-to-trough |
| Hard drawdown halt | 10.00% peak-to-trough |
| Maximum initial position value | 10.00% of equity |
| Maximum initial gross live exposure | 50.00% of equity |
| Maximum simultaneous live positions | 5 |
| Live leverage | 0 |

These values are maximums, not optimization targets. They may be reduced by later evidence but may not be increased without a mandate amendment.

## 6. Authorization Matrix

| Capability | Authorized? | Notes |
|---|:---:|---|
| Phase 01 research specification | YES | Define and pre-register one falsifiable strategy hypothesis |
| Strategy production code | NO | Wait for Phase 01 PASS and the applicable implementation phase |
| Data-vendor contract selection | NO | Phase 02 responsibility |
| Historical backtest execution | NO | Phase 03 responsibility after prior gates |
| Claimed performance or returns | NO | No results exist |
| Risk-engine implementation | NO | Phase 04 responsibility |
| Production architecture implementation | NO | Phase 05 responsibility |
| Schwab adapter implementation | NO | Broker contract must be verified first |
| Moomoo paper adapter implementation | NO | Paper behavior must be verified first |
| Telegram live approval implementation | NO | Security and fail-closed design pending |
| Paper order submission | NO | Later integration gates required |
| Live order submission | NO | Paper-to-live gates required |
| Live short selling | NO | Separate explicit decision required |

## 7. Known Facts, Decisions, and Assumptions

### 7.1 Approved decisions

- Phase 00 is complete with a PASS.
- Mandate v0.2 is approved and locked.
- The minimum limited-live capital gate is USD 5,000.
- Schwab is the provisional limited-live broker candidate.
- Moomoo is the provisional paper-trading candidate.
- Research may include long and short strategies.
- Initial limited live is long-only, no leverage, and no borrowed funds.
- Overnight and weekend holdings are permitted when strategy and risk rules allow them.
- Limited-live orders require daily arming and per-order Telegram approval.

### 7.2 Unverified external capabilities

The following must be treated as unverified until their later contract tests are complete:

- Schwab API authentication, account fields, rate limits, order types, token lifecycle, and short-related fields.
- Moomoo paper-account semantics and supported order behavior.
- Historical data-provider coverage, licensing, delistings, corporate actions, and point-in-time fields.
- Telegram security, identity, replay protection, availability, and approval auditability.

### 7.3 Prohibited assumptions

- That any strategy will generate alpha.
- That a backtest will pass.
- That paper fills predict live fills.
- That USD 5,000 makes every shortable security operationally feasible.
- That a broker API supports a field or workflow not verified by official documentation and contract tests.
- That a stop guarantees the planned exit price.
- That current index membership or current fundamentals are historically point-in-time correct.

## 8. Active Phase 01 Scope

Phase 01 must produce a falsifiable Strategy Research Specification containing at least:

1. The investment hypothesis and reason it may persist.
2. Exact eligible instruments and universe rules.
3. Exact mathematical signal definitions and timestamps.
4. Entry, exit, expiration, and do-not-trade rules.
5. Long/short treatment consistent with the staged mandate.
6. Benchmarks and simple baselines.
7. Transaction-cost and capacity assumptions to be validated later.
8. Pre-registered acceptance and rejection criteria.
9. Alternatives considered and unresolved risks.
10. A formal Phase 01 acceptance decision.

No final out-of-sample criterion may be changed after observing the final test results.

## 9. Open Issues Carried Forward

| ID | Issue | Blocking phase |
|---|---|---|
| OI-001 | Select one initial falsifiable strategy hypothesis | Phase 01 |
| OI-002 | Define exact universe, benchmark, and capacity assumptions | Phase 01 |
| OI-003 | Define exact signal and exit formulas | Phase 01 |
| OI-004 | Pre-register quantitative acceptance criteria | Phase 01 |
| OI-005 | Select and validate research-grade data | Phase 02 |
| OI-006 | Establish point-in-time universe and delisting treatment | Phase 02 |
| OI-007 | Define realistic transaction and short-borrow cost model | Phase 03 |
| OI-008 | Formalize deterministic risk state machine | Phase 04 |
| OI-009 | Verify Schwab broker contract | Phase 06 |
| OI-010 | Verify Moomoo paper contract | Phase 06/09 |
| OI-011 | Design secure Telegram approval workflow | Phase 06/07 |
| OI-012 | Verify whole-share feasibility under risk limits | Phase 01/04 |

## 10. Current Risks

- A small live account may make diversification and whole-share risk sizing difficult.
- Long/short research may be invalidated by missing point-in-time borrow and delisting data.
- Overnight and weekend gap risk may exceed planned stop-based risk.
- Laptop sleep, restart, updates, or network failure may interrupt live operations.
- Telegram approval can become an availability dependency and must fail closed.
- Broker and local state may diverge; new risk must remain blocked until reconciliation succeeds.

## 11. Next Three Concrete Tasks

1. Draft one candidate investment hypothesis consistent with the approved low-frequency mandate.
2. Define exact Phase 01 universe, signal, exit, abstention, baseline, and benchmark rules.
3. Pre-register measurable acceptance and rejection criteria before any final out-of-sample evaluation.

## 12. Machine-Readable Snapshot

```yaml
project:
  name: professional-local-algorithmic-trading-system
  environment: windows-11-local-laptop
  snapshot_date: 2026-08-05

phase:
  completed: "00 — Mandate Discovery"
  active: "01 — Strategy Research Specification"
  phase_00_result: PASS

mandate:
  version: "0.2"
  status: APPROVED_LOCKED
  live_capital_minimum_usd: 5000
  live_broker_candidate: schwab
  paper_broker_candidate: moomoo
  research_direction: long_short
  initial_live_direction: long_only
  horizon:
    - swing
    - position
  intraday_allowed: false
  overnight_allowed: true
  weekend_allowed: true
  data_budget_monthly_ceiling_usd: 80
  live_leverage_allowed: false
  live_margin_borrowing_allowed: false
  live_shorting_allowed: false

risk:
  planned_risk_per_position: 0.005
  aggregate_open_planned_risk: 0.02
  daily_loss_threshold: 0.01
  weekly_loss_threshold: 0.03
  drawdown_warning: 0.06
  hard_drawdown_halt: 0.10
  max_position_value: 0.10
  max_initial_gross_exposure: 0.50
  max_simultaneous_live_positions: 5

approval:
  daily_manual_arming: true
  per_order_telegram_approval: true
  llm_live_order_authority: false

implementation:
  phase_01_specification_authorized: true
  strategy_code_authorized: false
  backtest_authorized: false
  broker_integration_authorized: false
  paper_trading_authorized: false
  live_trading_authorized: false
```

## 13. State Update Rule

Update this file after every approved decision or phase result. The update must reference the applicable decision ID and must not alter locked mandate terms without a corresponding mandate amendment.

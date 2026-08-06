# Trading Mandate

> **Mandate version:** 0.2  
> **Status:** APPROVED — LOCKED  
> **Effective date:** 2026-08-05  
> **Approval decision:** DR-0004  
> **Phase 00 result:** PASS  
> **Next active phase:** 01 — Strategy Research Specification

## 1. Purpose and Authority

This document is the governing trading mandate for the Professional Local Algorithmic Trading System. It defines the approved financial, operational, risk, data, broker, and human-control boundaries that every later phase must inherit.

The mandate is subordinate only to the project's master governing specification. When another project document conflicts with this mandate, work must stop until the conflict is resolved through a numbered decision and an approved mandate amendment.

This mandate does **not** establish that any strategy has an edge. Every strategy remains an unproven hypothesis until it passes the required research, statistical, operational, and risk gates.

## 2. Governing Priorities

The system shall optimize in this order:

1. Capital preservation and fail-closed behavior.
2. Evidence-based, reproducible development.
3. Risk-adjusted return.
4. Absolute return.

A missed trade is preferable to an unsafe trade. No risk limit may be bypassed to recover a loss or to make a proposed trade fit.

## 3. Approved Mandate Summary

| Dimension | Approved boundary |
|---|---|
| Initial research direction | Long and short |
| Initial limited-live direction | Long-only |
| Primary horizon | Swing and position trading |
| Expected holding period | Approximately 2 trading days to several months |
| Signal frequency | Daily, end-of-day, or otherwise low-frequency |
| Intraday strategies | Not permitted in the initial mandate |
| Overnight holdings | Permitted, subject to strategy and risk rules |
| Weekend holdings | Permitted, subject to event and gap-risk rules |
| Limited-live capital gate | Minimum USD 5,000 funded capital |
| Provisional live broker candidate | Charles Schwab |
| Provisional paper broker candidate | Moomoo |
| Initial live leverage | Prohibited |
| Initial live margin borrowing | Prohibited |
| Initial live direct shorting | Prohibited until a separate acceptance decision |
| Monthly recurring data budget ceiling | USD 80 initially |
| Human control | Daily manual arming and per-order Telegram approval for limited live |
| Primary operating environment | Local Windows 11 laptop |

## 4. Environment Separation

The following environments must remain physically and logically separated:

- Research and exploratory analysis.
- Historical vectorized backtesting.
- Event-driven simulation.
- Broker paper trading.
- Limited live trading.

Each environment must use separate configuration, credentials, state, logs, databases, and safety permissions. Live credentials must not be available to ordinary research scripts or notebooks.

No result from one environment may be represented as evidence from another. In particular, paper fills are not live fills, and a historical backtest is not proof of profitability.

## 5. Instruments and Market Scope

### 5.1 Initially eligible for research

- U.S.-listed common equities.
- Selected broad-market and sector exchange-traded funds.
- Regular exchange listings with sufficient price, liquidity, history, and data completeness.

Exact exchanges, minimum price, market-cap constraints, liquidity thresholds, spread constraints, trading-history requirements, and universe-reconstruction rules must be defined and approved in Phase 01 and Phase 02.

### 5.2 Initially excluded

- OTC securities.
- Penny stocks.
- Illiquid micro-cap securities.
- Options.
- Futures.
- Cryptocurrencies.
- Leveraged and inverse ETFs.
- Pre-market and after-hours execution.
- Intraday or high-frequency strategies.
- Live margin borrowing.
- Immediate live short selling.
- Discretionary averaging down.
- Autonomous LLM trading decisions.

An excluded category may be researched only after an approved amendment or later-phase decision explicitly permits it.

## 6. Deployment Stages

### 6.1 Research and historical testing

Long and short signals may be researched. Historical short testing must eventually include conservative treatment of borrow availability, borrow fees, dividend liabilities, recalls, forced buy-ins, execution costs, and position constraints. Missing short-cost or borrow information must be disclosed and may require disabling the short-side conclusion.

### 6.2 Paper trading

Long and short behavior may be paper traded where the selected broker environment supports the required order and account semantics. Paper trading is an integration and behavior test; it is not evidence of live profitability.

### 6.3 Initial limited live

Limited live trading may begin only after all applicable paper-to-live gates pass and at least USD 5,000 is funded with the approved broker.

The initial limited-live stage is restricted to:

- Long-only positions.
- No borrowed cash.
- No leverage.
- No direct short positions.
- Regular-market-hours order submission.
- Daily manual arming.
- Manual approval of every proposed order.
- No automatic capital scaling.

The exact broker account registration may be cash or margin-approved as required by the verified broker contract, but the economic operating mode is locked: the system may not borrow funds or create leverage during the initial limited-live stage.

### 6.4 Restricted live shorting

Live shorting remains disabled until all of the following are satisfied:

1. The complete strategy passes pre-registered historical acceptance criteria.
2. Long-side and short-side results are reported separately.
3. Short-side results survive conservative transaction, borrow, dividend, recall, and execution costs.
4. Paper trading validates short-order behavior and reconciliation.
5. The live account has verified permissions for margin and short selling.
6. Borrow availability is checked before every short order.
7. Borrow fees are available or conservatively bounded.
8. Dividend liabilities are modeled and reconciled.
9. Recall, forced-buy-in, rejection, partial-fill, and margin-call scenarios pass testing.
10. The system cannot confuse sell-to-close, sell-short, and buy-to-cover actions.
11. Broker and local positions and orders reconcile correctly.
12. Restart, duplicate-order, idempotency, and failure-recovery tests pass.
13. A separate numbered decision explicitly authorizes restricted live shorting.

Meeting the USD 5,000 capital gate alone does not authorize short selling.

## 7. Approved Risk Limits

The following limits apply at the initial USD 5,000 limited-live capital level. They are maximums, not targets, and later phases may reduce them.

| Risk control | Approved limit | USD equivalent at USD 5,000 |
|---|---:|---:|
| Planned risk per position | 0.50% of equity | USD 25 |
| Aggregate open planned risk | 2.00% of equity | USD 100 |
| Daily loss threshold | 1.00% of start-of-day equity | USD 50 |
| Weekly loss threshold | 3.00% of week-start equity | USD 150 |
| Drawdown warning | 6.00% peak-to-trough | USD 300 |
| Hard drawdown halt | 10.00% peak-to-trough | USD 500 |
| Maximum initial position market value | 10.00% of equity | USD 500 |
| Maximum initial gross live exposure | 50.00% of equity | USD 2,500 |
| Maximum simultaneous live positions | 5 | — |
| Live leverage | 0 | — |

### 7.1 Provisional sizing formula

The detailed sizing model is a Phase 04 deliverable. Until then, the approved conceptual boundary is:

```text
risk_budget = account_equity × 0.005
per_share_risk = abs(planned_entry_price - protective_exit_price)
raw_quantity = floor(risk_budget / per_share_risk)
```

The final approved quantity must also satisfy position-value, liquidity, buying-power, correlation, sector, gross-exposure, gap-risk, and broker constraints.

When one whole share exceeds an applicable risk or position limit, the correct quantity is zero and the trade is skipped. Protective stops limit planned risk but do not guarantee execution price or eliminate overnight gap risk.

### 7.2 Risk-limit change control

Risk limits may not be increased merely to improve a backtest, avoid rejecting a trade, or recover a loss. Any increase requires:

- A numbered mandate amendment.
- Documented rationale and evidence.
- Analysis of impact on prior research and acceptance criteria.
- Explicit user approval.
- An update to the current-state and decision-log documents.

## 8. Risk States and Fail-Closed Behavior

The deterministic risk engine will later formalize the complete state machine. The mandate requires at least the following operational intent:

| State | Required behavior |
|---|---|
| `NORMAL` | Operate within all approved rules and limits. |
| `NO_NEW_POSITIONS` | Manage existing risk, but reject new exposure. |
| `EXIT_ONLY` | Permit only risk-reducing actions that can be submitted safely. |
| `HALTED` | Submit no strategy-driven orders; require investigation and controlled recovery. |
| `MANUAL_REVIEW_REQUIRED` | Do not resume until the discrepancy is explicitly resolved and recorded. |

The system must not open new positions when a critical input is missing, stale, inconsistent, or unverifiable. Fail-closed triggers include, but are not limited to:

- Stale, missing, or invalid market data.
- Broken or unknown corporate-action adjustment.
- Market-calendar or clock uncertainty.
- Unknown broker position or order state.
- Broker/local reconciliation mismatch.
- Duplicate-order or idempotency uncertainty.
- Risk-calculation failure.
- Database durability or write failure.
- Broker connectivity loss.
- Abnormal price, spread, volatility, or liquidity.
- Unknown short-borrow status for a proposed short.
- Strategy or configuration version mismatch.
- Telegram approval unavailable or unverifiable for limited live.

The broker account is authoritative for orders, fills, and positions. Local state is an operational cache and must not override verified broker state.

## 9. Human Approval and Telegram Control

### 9.1 Paper environment

Paper orders may execute automatically only after deterministic strategy and risk checks pass. Telegram may notify, pause, or request optional review, but must not be the sole safety mechanism.

### 9.2 Limited-live environment

Limited-live trading requires:

1. Manual daily arming.
2. Manual approval of every proposed order through Telegram.
3. An immutable deterministic order-intent identifier.
4. A defined approval expiration time.
5. Automatic invalidation when symbol, side, intended action, quantity, price constraints, strategy version, or risk context changes outside approved tolerances.
6. Automatic rejection when approval cannot be authenticated or has expired.

Each approval request must contain at least:

- Order-intent ID.
- Strategy and configuration version.
- Symbol and intended action.
- Quantity.
- Proposed order type and price constraint.
- Estimated position value.
- Planned position risk.
- Current portfolio exposure.
- Deterministic entry or exit rationale.
- Approval-expiration timestamp.

Free-form messages must not directly create, resize, replace, cancel, or authorize an order.

## 10. Deterministic Trade Path and LLM Boundary

An LLM may assist with research ideation, documentation, explanations, journal summaries, and failure diagnosis.

An LLM must never directly:

- Select a live security outside deterministic rules.
- Decide whether to place a live order.
- Change quantity or position size.
- Override risk limits.
- Modify stops or exits.
- Submit, replace, cancel, or approve an order.

Every live decision must be produced by version-controlled deterministic code with recorded inputs and reproducible state transitions.

## 11. Data Budget and Data Governance

The initial recurring data-budget ceiling is USD 80 per month.

Provider selection is not approved by this mandate. Later phases must verify provider contracts, including:

- Historical coverage and licensing.
- Timestamps and availability semantics.
- Corporate actions and symbol changes.
- Delisted-security and historical-universe coverage.
- Point-in-time integrity.
- Rate limits and caching/export rights.
- Data quality and outage behavior.
- Reproducibility requirements.

Free or development-grade data may be used for interface prototyping, but must not be represented as research-grade, exchange-grade, or production-reliable.

Fundamental data is deferred unless a pre-registered strategy hypothesis requires it.

## 12. Operating Constraints

The platform will initially run on a local Windows 11 laptop that is expected to be available primarily during U.S. trading hours.

Because the selected mandate is low-frequency, signal research and order preparation should be designed around end-of-day or scheduled processing rather than continuous intraday uptime. Before any live session, the platform must eventually verify power, connectivity, clock synchronization, market status, broker connectivity, reconciliation, storage, secrets, alerts, and kill-switch availability.

Sleep, restart, network loss, or application failure must enter a non-trading recovery mode. The system may resume only after durable-state restoration and broker reconciliation succeed.

## 13. Items Deferred to Later Phases

The following remain intentionally unresolved:

- Exact investment hypothesis.
- Exact universe and benchmark.
- Signal, entry, exit, expiration, and abstention formulas.
- Research data provider.
- Point-in-time universe and delisting solution.
- Transaction-cost and short-borrow model.
- Schwab API contract and account permissions.
- Moomoo paper-account behavior.
- Telegram authentication and authorization design.
- Full risk-state transition table.
- Whole-share feasibility under the approved position-risk budget.

No deferred item may be filled with an undocumented assumption.

## 14. Non-Authorization Statement

Approval of this mandate authorizes Phase 01 specification work only. It does not authorize:

- Strategy implementation.
- Backtest execution or claimed results.
- Broker integration.
- Live credentials.
- Paper or live order submission.
- Live trading.
- Live short selling.

Each capability requires completion of its corresponding sequential phase and acceptance gate.

## 15. Amendment Procedure

This mandate is locked. A material change to capital, broker, account operating mode, direction, horizon, instruments, risk limits, data budget, leverage, live-short permission, or human approval requires:

1. A new decision-log entry.
2. A versioned mandate amendment.
3. A documented reason and impact assessment.
4. Explicit approval.
5. Updates to `docs/project/CURRENT_STATE.md`, `docs/project/DECISIONS.md`, and affected phase records.

Silent changes are prohibited.

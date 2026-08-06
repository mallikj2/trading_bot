# Phase 00 — Mandate Discovery

> **Phase status:** PASS  
> **Completed:** 2026-08-05  
> **Approved mandate:** v0.2  
> **Acceptance decision:** DR-0004  
> **Next phase:** 01 — Strategy Research Specification

## 1. Objective

Resolve the investor, account, broker, risk, data, approval, holding-period, and local-computer constraints before defining or implementing a trading strategy.

Phase 00 intentionally stops before strategy code, backtesting, broker integration, or production architecture. Its purpose is to establish a coherent mandate that can be falsified and implemented safely in later sequential phases.

## 2. Governing Principles Applied

- Treat every strategy as an unproven hypothesis.
- Preserve capital before pursuing return.
- Prefer evidence before complexity.
- Fail closed when state or critical inputs are uncertain.
- Separate research, historical testing, paper trading, and live trading.
- Keep live decisions deterministic and version controlled.
- Do not invent broker behavior, data availability, tests, fills, or performance.
- Do not silently change approved requirements.

## 3. Inputs Reviewed

### 3.1 Governing project input

The master governing specification required:

- Identification of conflicts among capital, horizon, data, shorting, laptop availability, and risk expectations.
- No more than twelve critical mandate questions.
- Three differentiated feasible mandate alternatives.
- A recommended initial path.
- A formal PASS, CONDITIONAL PASS, or FAIL decision.

### 3.2 User mandate responses

| # | Question | Initial response | Final resolved mandate |
|---:|---|---|---|
| 1 | Starting capital | USD 1,000 initially | USD 5,000 minimum for limited live; research may start unfunded |
| 2 | Account type | Undecided | Broker registration deferred; initial live may not borrow or use leverage |
| 3 | Broker | Schwab and Moomoo | Schwab provisional live candidate; Moomoo provisional paper candidate |
| 4 | Direction | Long and short | Long/short research; long-only initial limited live |
| 5 | Horizon | Swing and position | Approved; intraday excluded initially |
| 6 | Overnight exposure | Undecided | Overnight and weekend holdings permitted under explicit risk/event rules |
| 7 | Maximum drawdown | 50% | Replaced by 6% warning and 10% hard halt |
| 8 | Maximum daily loss | 20% | Replaced by 1% daily threshold |
| 9 | Risk per trade | 15% | Replaced by 0.50% planned risk per position |
| 10 | Data budget | Approximately USD 50–100, undecided | USD 80 monthly recurring ceiling initially |
| 11 | Human approval | Telegram approval considered | Daily manual arming plus per-order Telegram approval for limited live |
| 12 | Computer availability | Primarily U.S. trading hours | Accepted for low-frequency design; reliability gates remain mandatory |

## 4. Conflicts Identified

### 4.1 Initial capital versus live long/short operation

USD 1,000 was incompatible with a prudent diversified live long/short deployment. Direct shorting also adds borrow, margin, recall, dividend-liability, forced-buy-in, and reconciliation dependencies.

**Resolution:** Preserve long/short as a research objective, increase the limited-live capital gate to USD 5,000, begin limited live long-only, and keep live shorting behind a separate acceptance gate.

### 4.2 Submitted loss limits versus capital preservation

At USD 1,000, the submitted values would have allowed approximately USD 150 planned risk on one trade, USD 200 daily loss, and USD 500 drawdown before review.

**Resolution:** Replace them with 0.50% planned risk per position, 1.00% daily loss threshold, 3.00% weekly threshold, 6.00% drawdown warning, and 10.00% hard halt.

### 4.3 Swing/position horizon versus undecided overnight exposure

A multi-day or multi-month strategy cannot generally avoid overnight and weekend exposure without becoming a materially different strategy.

**Resolution:** Permit overnight and weekend holdings, while requiring explicit earnings, corporate-action, volatility, liquidity, and gap-risk abstention rules in Phase 01 and later risk work.

### 4.4 Laptop availability versus intraday reliability

A local laptop available mainly during U.S. trading hours is a weak foundation for continuous intraday state management and rapid recovery.

**Resolution:** Select daily/end-of-day or otherwise low-frequency operation and exclude intraday strategies from the initial mandate.

### 4.5 Data budget versus broad point-in-time coverage

A USD 50–100 monthly budget may not support every desired combination of long history, delistings, point-in-time fundamentals, consolidated real-time data, corporate actions, and borrow history.

**Resolution:** Set an initial USD 80 ceiling, defer provider selection to Phase 02, keep fundamentals optional, and prohibit unsupported data claims.

### 4.6 Telegram convenience versus deterministic safety

A chat channel can be unavailable, spoofed, replayed, or ambiguous and therefore cannot be the strategy or sole safety control.

**Resolution:** Use Telegram only as an authenticated approval interface for immutable deterministic order intents. Approval failure must block new live risk.

## 5. Alternatives Considered

| Dimension | Alternative A — EOD Long-Only Swing | Alternative B — Intraday Liquid Equities | Alternative C — Long/Short Low-Frequency Portfolio |
|---|---|---|---|
| Instruments | Liquid U.S. equities and broad ETFs | Small set of highly liquid equities/ETFs | Liquid U.S. equities and selected ETFs |
| Horizon | Approximately 2–20 trading days | Minutes to same-day close | Approximately 2 days to several weeks/months |
| Signal frequency | Daily/end-of-day | Intraday bars/events | Daily or weekly |
| Data burden | Low to moderate | High and real-time dependent | Moderate to high, especially for short data |
| Shorting | No | Optional but not recommended initially | Required for full implementation |
| Operational complexity | Low to moderate | High | High |
| Laptop feasibility | Strong | Weak to moderate | Good for research; harder for live short operations |
| Principal risks | Gap risk and market beta | Slippage, outages, partial fills, rapid losses | Borrow cost/availability, recalls, crowding, margin and factor exposure |
| Initial implementation difficulty | 2/5 | 4/5 | 5/5 |

### Alternative A decision

Operationally safest initial production candidate but did not fully preserve the user's long/short research objective.

### Alternative B decision

Rejected for the initial mandate because it conflicts with the laptop environment, data budget, reliability burden, and chosen swing/position horizon.

### Alternative C decision

Selected as the research direction, but staged so that the initial limited-live implementation remains long-only and unleveraged.

## 6. Selected Mandate

The approved mandate is a **staged low-frequency long/short research platform with long-only initial limited live**.

### 6.1 Research scope

- Research may evaluate long and short hypotheses.
- Strategies must be interpretable and falsifiable.
- Exact rules and criteria must be pre-registered before final out-of-sample evaluation.
- Short-side conclusions must eventually include realistic borrow and execution treatment.

### 6.2 Limited-live scope

- Minimum funded capital: USD 5,000.
- Provisional live broker candidate: Charles Schwab.
- Long-only.
- No leverage or borrowed cash.
- Regular-market-hours execution only.
- Maximum five simultaneous positions.
- Daily manual arming.
- Per-order Telegram approval.
- No automatic capital scaling.

### 6.3 Paper scope

- Moomoo is the provisional paper broker candidate.
- Long and short paper behavior may be evaluated only after the relevant broker contract is verified.
- Paper behavior is not evidence of profitability or live execution quality.

## 7. Approved Risk Boundaries

| Risk control | Approved limit | USD equivalent at USD 5,000 |
|---|---:|---:|
| Planned risk per position | 0.50% | USD 25 |
| Aggregate open planned risk | 2.00% | USD 100 |
| Daily loss threshold | 1.00% | USD 50 |
| Weekly loss threshold | 3.00% | USD 150 |
| Drawdown warning | 6.00% | USD 300 |
| Hard drawdown halt | 10.00% | USD 500 |
| Maximum position market value | 10.00% | USD 500 |
| Maximum initial gross exposure | 50.00% | USD 2,500 |
| Maximum simultaneous positions | 5 | — |
| Live leverage | 0 | — |

These are maximums and may be tightened by later evidence. They may not be increased without a formal mandate amendment.

## 8. Human-Control Decision

### Paper

Automatic paper execution may eventually be allowed after deterministic strategy and risk checks pass. Telegram is supplemental and may provide notification or pause controls.

### Limited live

Every live order requires:

- A deterministic immutable order-intent ID.
- Current strategy and configuration version.
- Symbol, side/action, quantity, and price constraints.
- Planned risk and current exposure.
- Deterministic rationale.
- Approval expiry.
- Authenticated Telegram approval.

Any material modification invalidates the approval. Free-form chat may not directly submit or alter an order. An LLM has no live-order authority.

## 9. Facts, Assumptions, Recommendations, and Decisions

### 9.1 Facts recorded from the user

- Schwab and Moomoo accounts are available or preferred.
- The intended research direction is long and short.
- The preferred horizon is swing and position.
- The laptop is expected to be available primarily during U.S. trading hours.
- Funding USD 5,000 for limited live is acceptable.

### 9.2 Assumptions requiring later verification

- Exact Schwab account and API capabilities.
- Exact Moomoo paper-account capabilities.
- Availability and quality of point-in-time historical data within budget.
- Operational feasibility of Telegram approval security.
- Whole-share feasibility under approved risk limits.

### 9.3 Recommendations adopted

- Use a staged research-to-live path.
- Begin limited live long-only and unleveraged.
- Use conservative risk limits.
- Use low-frequency operation compatible with a local laptop.
- Defer live shorting until independently validated.

### 9.4 Approved decisions

- Mandate v0.2 is locked.
- Phase 00 is complete.
- Phase 01 specification work is authorized.
- No implementation, backtest, broker integration, or trading is yet authorized.

## 10. Deferred Items

The following were intentionally deferred rather than assumed:

- Exact investment hypothesis.
- Exact universe and benchmark.
- Mathematical signal and exit definitions.
- Do-not-trade conditions.
- Research data provider.
- Point-in-time data design.
- Cost and borrow model.
- Risk state-machine transitions.
- Broker API contracts.
- Telegram security design.
- Paper-to-live evidence requirements beyond the governing specification.

## 11. Acceptance Gate

| Requirement | Result | Evidence or resolution |
|---|:---:|---|
| Starting capital defined | PASS | USD 5,000 limited-live minimum |
| Account operating mode defined | PASS | No initial borrowed cash or leverage; registration details deferred to broker verification |
| Broker preference recorded | PASS | Schwab live candidate; Moomoo paper candidate |
| Direction defined | PASS | Long/short research; long-only initial live |
| Horizon defined | PASS | Swing and position; low-frequency |
| Overnight policy defined | PASS | Permitted under explicit rules |
| Drawdown limit defined | PASS | 6% warning; 10% hard halt |
| Daily loss limit defined | PASS | 1% |
| Per-position risk defined | PASS | 0.50% |
| Data budget defined | PASS | USD 80 monthly ceiling |
| Human approval defined | PASS | Daily arming plus per-order Telegram approval |
| Computer availability addressed | PASS | Low-frequency mandate selected |
| Conflicts resolved | PASS | Staged deployment adopted |
| Mandate explicitly approved | PASS | `APPROVE MANDATE V0.2` |

## 12. Failure Modes Carried Forward

- Whole-share positions may exceed approved risk or value limits.
- Overnight gaps may exceed planned stop risk.
- Long/short research may be biased by missing delistings or borrow history.
- Data or corporate-action defects may contaminate signals.
- Broker/local state may diverge.
- Telegram may be unavailable or unauthenticated.
- Laptop sleep, updates, restart, or network loss may interrupt operation.
- Broker order semantics may differ from assumptions.

Each condition must block or constrain trading as appropriate; none may be dismissed merely because it reduces opportunity.

## 13. Decision Record

| Decision ID | Summary | Status |
|---|---|---|
| DR-0001 | Open Phase 00 and withhold implementation | Completed |
| DR-0002 | Propose staged Mandate v0.1 | Superseded |
| DR-0003 | Set USD 5,000 Schwab limited-live capital gate | Incorporated into v0.2 |
| DR-0004 | Approve Mandate v0.2 and close Phase 00 | Approved — active |

## 14. Implementation Plan for This Phase

Phase 00 required governance documentation only. No strategy or trading implementation was appropriate.

Completed deliverables:

- Trading mandate.
- Current-state record.
- Decision log.
- Phase 00 discovery and acceptance record.

No tests, backtest results, API calls, broker responses, or performance claims are recorded because none were executed in Phase 00.

## 15. Next Three Concrete Tasks

1. Select and articulate one falsifiable low-frequency investment hypothesis.
2. Define exact universe, signal, entry, exit, abstention, benchmark, and baseline rules.
3. Pre-register Phase 01 quantitative acceptance and rejection criteria before implementation or final out-of-sample testing.

## 16. Phase Result

**PASS — Phase 00 is complete. Proceed to Phase 01 — Strategy Research Specification.**

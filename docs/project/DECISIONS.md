# Project Decision Log

> **Log type:** Append-only governance record  
> **Current mandate:** v0.2 — APPROVED and LOCKED  
> **Current phase:** 01 — Strategy Research Specification  
> **Last decision:** DR-0004

## 1. Decision-Log Rules

- Every material project decision receives a unique sequential ID.
- Existing entries are not deleted or rewritten to hide history.
- A superseded decision remains in the log with its status and replacement reference.
- Material changes require the reason, consequences, affected documents, and explicit approval.
- Facts, assumptions, recommendations, and decisions must not be conflated.
- No decision entry may claim a test, result, broker response, or performance outcome that did not occur.

The next available decision identifier is **DR-0005**.

---

## DR-0001 — Open Phase 00 Mandate Discovery

| Field | Value |
|---|---|
| Date | 2026-08-05 |
| Status | COMPLETED |
| Type | Phase initiation |
| Decision | Begin Phase 00 and withhold implementation until the mandate is resolved. |

### Context

The project had a governing specification but no approved mandate, project-state record, or acceptance-gate record. The system could not safely proceed to strategy implementation without resolving capital, account, broker, direction, horizon, risk, data, approval, and operating constraints.

### Consequences

- Phase 00 became the active phase.
- No strategy, backtest, broker integration, or production implementation was authorized.
- Twelve mandate questions and three feasible alternatives were required.

### Affected documents

- `docs/phases/PHASE_00_MANDATE_DISCOVERY.md`
- `docs/project/CURRENT_STATE.md`

---

## DR-0002 — Propose Staged Mandate v0.1

| Field | Value |
|---|---|
| Date | 2026-08-05 |
| Status | SUPERSEDED |
| Type | Mandate proposal |
| Superseded by | DR-0003 and DR-0004 |
| Decision | Propose long/short research with long-only initial limited live and conservative replacement risk limits. |

### Context

The initial answers specified approximately USD 1,000, a desired long/short strategy, swing and position horizons, undecided overnight exposure, very high proposed loss limits, an approximately USD 50–100 data budget, Telegram approval, and laptop availability during U.S. trading hours.

The original proposed risk limits—15% per trade, 20% daily loss, and 50% portfolio drawdown—were incompatible with the project's capital-preservation priority.

### Proposed resolution

- Research and paper testing could include long and short behavior.
- Initial limited live would be long-only, no leverage, and no borrowed cash.
- Planned risk per position would be reduced to 0.50%.
- Daily loss threshold would be reduced to 1.00%.
- Hard drawdown halt would be reduced to 10.00%.
- Initial recurring data-budget ceiling would be USD 80.
- Moomoo would be a provisional paper candidate and Schwab a provisional live candidate.

### Consequences

This entry established the staged structure but was not the final approved mandate because the live-capital target was subsequently amended.

### Affected documents

- `docs/governance/TRADING_MANDATE.md`
- `docs/phases/PHASE_00_MANDATE_DISCOVERY.md`

---

## DR-0003 — Set USD 5,000 Schwab Limited-Live Capital Gate

| Field | Value |
|---|---|
| Date | 2026-08-05 |
| Status | INCORPORATED INTO MANDATE v0.2 |
| Type | Mandate amendment |
| Decision | Set USD 5,000 as the minimum funded-capital gate for limited-live trading with Schwab as the provisional live broker candidate. |

### Rationale

The user explicitly accepted funding USD 5,000 for live trading. The larger capital base improves whole-share feasibility and provides a more conservative operational buffer than the initial USD 1,000 concept.

The capital gate does not itself authorize leverage or short selling.

### Locked consequences

- Historical research may begin without funding USD 5,000.
- Paper trading may begin only after its applicable phases and gates.
- Limited-live launch requires at least USD 5,000 funded capital.
- Initial limited live remains long-only, no borrowed funds, and no leverage.
- Direct live shorting remains behind an independent validation and approval gate.
- Risk-limit dollar equivalents are based initially on USD 5,000 equity.

### Affected documents

- `docs/governance/TRADING_MANDATE.md`
- `docs/project/CURRENT_STATE.md`
- `docs/phases/PHASE_00_MANDATE_DISCOVERY.md`

---

## DR-0004 — Approve Mandate v0.2 and Close Phase 00

| Field | Value |
|---|---|
| Date | 2026-08-05 |
| Status | APPROVED — ACTIVE |
| Type | Mandate approval and phase gate |
| Approval evidence | User instruction: `APPROVE MANDATE V0.2` |
| Decision | Approve and lock Mandate v0.2; issue PASS for Phase 00; activate Phase 01. |

### Approved mandate

- Minimum limited-live capital: USD 5,000.
- Provisional limited-live broker candidate: Charles Schwab.
- Provisional paper broker candidate: Moomoo.
- Research direction: long and short.
- Initial limited-live direction: long-only.
- Horizon: swing and position.
- Intraday strategies: excluded initially.
- Overnight and weekend holdings: permitted subject to strategy and risk rules.
- Initial live leverage and borrowed cash: prohibited.
- Initial live short selling: prohibited pending separate acceptance.
- Initial recurring data-budget ceiling: USD 80 per month.
- Limited-live human control: daily manual arming plus per-order Telegram approval.

### Approved risk limits

| Control | Limit |
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

### Phase-gate result

**PASS — Phase 00 is complete. Proceed to Phase 01.**

### Authorization boundary

This decision authorizes Phase 01 specification work only. It does not authorize strategy code, backtesting, broker integration, paper trading, live trading, or live shorting.

### Affected documents

- `docs/governance/TRADING_MANDATE.md`
- `docs/project/CURRENT_STATE.md`
- `docs/project/DECISIONS.md`
- `docs/phases/PHASE_00_MANDATE_DISCOVERY.md`

---

## 2. Pending Decision Areas

The following are unresolved and must receive future decisions at the appropriate phase:

- Initial strategy hypothesis and Phase 01 acceptance criteria.
- Exact universe, benchmark, and trading rules.
- Research-grade data provider and point-in-time data contract.
- Backtesting methodology and cost assumptions.
- Deterministic risk-state transition rules.
- Schwab broker contract and supported workflows.
- Moomoo paper-trading contract and supported workflows.
- Telegram security and approval protocol.
- Paper-to-live evidence and limited-live authorization.
- Restricted live-short authorization.

## 3. Decision Template

Use the following structure for future entries:

```markdown
## DR-XXXX — Decision title

| Field | Value |
|---|---|
| Date | YYYY-MM-DD |
| Status | PROPOSED / APPROVED / REJECTED / SUPERSEDED |
| Type | Category |
| Decision | Exact decision statement |

### Context

### Alternatives considered

### Rationale

### Consequences

### Acceptance or rollback conditions

### Affected documents
```

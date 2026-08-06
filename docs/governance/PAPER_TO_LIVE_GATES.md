# Paper-to-Live Gates

## Status

**NOT ELIGIBLE — current phase is mandate discovery.**

Paper trading is an integration test, not proof of profitability. Live trading remains prohibited until every applicable gate below has documented evidence and an explicit decision record.

## Historical research gates

- Falsifiable hypothesis approved
- Exact mandate approved
- Baselines implemented
- Point-in-time limitations documented
- Leakage tests passed
- Walk-forward and protected final out-of-sample process completed
- Multiple-testing history reported
- Conservative costs modeled
- Parameter-neighborhood stability evaluated
- Regime and ablation results reported
- Pre-registered criteria satisfied without post-hoc weakening

## Paper-trading gates

- Broker adapter contract tests passed
- Intended strategy behavior matched observed paper behavior
- Duplicate-order prevention passed
- Partial-fill handling passed
- Rejection and timeout handling passed
- Data-staleness fail-closed tests passed
- Position and open-order reconciliation passed
- Crash, restart, sleep, and network-recovery tests passed
- Kill-switch tests passed
- Alert failure did not compromise safety
- No unresolved critical defects remain
- Minimum number of sufficiently independent paper decisions reached

## Limited-live controls

The first live stage must use:

- No leverage unless separately approved
- Long-only unless shorting has separately passed all gates
- One-share or tightly capped capital
- Small maximum total exposure
- Manual daily arming
- Strict daily loss limit
- No automatic capital scaling
- Broker and local reconciliation before new orders
- Immediate fail-closed behavior on critical uncertainty

## Live comparison requirements

Compare actual live behavior against:

- Historical cost assumptions
- Event-driven simulation
- Broker paper fills
- Expected spread and slippage
- Expected reject, cancel, and partial-fill behavior

Capital may increase only through a new recorded decision after execution and risk behavior remain within documented tolerances.

## Gate decision

- Current decision: `FAIL — not eligible for paper or live trading`
- Reason: Mandate, strategy, data, backtesting, risk, architecture, broker safety, and operations phases are incomplete.

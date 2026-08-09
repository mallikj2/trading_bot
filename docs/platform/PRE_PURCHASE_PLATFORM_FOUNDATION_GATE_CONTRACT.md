# Pre-Purchase Platform Foundation Gate Contract

**Gate:** `P02-PF-GATE`  
**Phase:** Phase 02B  
**Purpose:** Prove PF01–PF10 operate coherently as a local, deterministic, synthetic platform before any commercial account/license procurement.

## Hard boundaries

The gate MUST NOT:

- connect to Schwab or any live broker;
- submit a live or deployed paper order;
- require commercial market-data credentials;
- authorize procurement automatically;
- authorize Phase 03;
- claim that `CSMOM-LS-v0.2` is profitable;
- rewrite any previously approved Phase 02 data gate.

## Mandatory checks

1. **All PF tasks pass** — PF01 through PF10 are individually `PASS`.
2. **Strategy validation controls** — clean lookahead/recursive fixtures pass and deliberately contaminated controls fail.
3. **TradeLead + Watchlist** — deterministic lead identity/idempotency and explicit blocker reasons.
4. **Simulation + OMS + journal/replay** — synthetic order flow is journal-complete and deterministic across reopen/rerun.
5. **Runtime-state enforcement** — `REDUCING` blocks new exposure; `ACTIVE` does not imply live authority.
6. **Recovery/reconciliation** — crash-window broker truth is reconciled without duplicate submission.
7. **Alert/incident integration** — reconciliation findings produce an immutable incident lifecycle.
8. **Experiment lineage** — the integrated runtime hash is bound to immutable `SIMULATION_ONLY` experiment evidence.
9. **Read-only UI/API + zero live mutation** — integrated state is visible through GET-only API and simulated broker remains network-free.
10. **No embedded commercial credentials** — no known secret files or credential token material in the repository bundle.

## PASS semantics

A PASS changes only procurement readiness:

```text
P02-PF-GATE = PASS
PROCUREMENT_READY_FOR_MANUAL_APPROVAL = true
PROCUREMENT_AUTHORIZED = false
PHASE03_AUTHORIZED = false
STRATEGY_PROFITABILITY_VALIDATED = false
```

The next action is a manual provider/account/license procurement review. Actual spend or credential entry requires explicit governance/user approval.

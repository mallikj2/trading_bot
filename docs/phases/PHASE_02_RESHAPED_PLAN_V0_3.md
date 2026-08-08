# Phase 02 — Reshaped Plan v0.3

**Date:** 2026-08-08  
**Status:** ACTIVE / RESHAPED  
**Phase 03 authorization:** DENIED  
**Commercial procurement authorization:** DEFERRED UNTIL PRE-PURCHASE PLATFORM FOUNDATION PASSES

## 1. Purpose of this revision

Phase 02 has successfully built most of the internal data-integrity foundation required by the approved Phase 01 strategy. The remaining seven data gates depend primarily on external provider accounts, licenses, credentials, or real historical coverage evidence.

Before purchasing those accounts, Phase 02 is expanded with a mandatory **Pre-Purchase Platform Foundation** workstream. This workstream adds the operational and research-product capabilities identified from mature systematic trading platforms while preserving every previously approved Phase 00/01 requirement and every existing Phase 02 data gate.

This revision does **not**:

- change `CSMOM-LS-v0.2` signal mathematics;
- authorize Phase 03 acceptance backtesting;
- authorize deployed paper trading;
- authorize live trading;
- authorize order submission;
- relax any existing point-in-time/data-provider gate;
- change the approved long/short, sizing, timing, universe, or cost rules.

## 2. Phase 02 is now organized into four subphases

### Phase 02A — Data and Point-in-Time Foundation

**Status:** substantially implemented; external evidence gates remain open.

This contains all work completed so far, including:

- Phase 01 reconciliation;
- minimum data kernel;
- provider adapters;
- point-in-time identity;
- historical sector engine;
- corporate actions and total returns;
- earnings revision engine;
- spread/transaction-cost engine;
- short-borrow engine;
- financing/cash-carry engine;
- regulatory fee history;
- PIT security-master/execution integration;
- SEC sector-coverage crawler;
- provider reconciliation tooling.

The existing 18 Phase 02 data gates remain authoritative and unchanged.

### Phase 02B — Pre-Purchase Platform Foundation

**Status:** NEW / NOT STARTED.

All ten tasks below must pass before commercial account/license procurement begins.

The objective is to build and test the application's internal product/runtime shell using synthetic data, committed fixtures, deterministic clocks, mock providers, and simulated brokers.

### Phase 02C — External Account, License, and Credentialed Evidence

**Status:** DEFERRED.

Begins only after Phase 02B receives PASS and a manual procurement decision is recorded.

This stage obtains the minimum external accounts/licenses required to close P02-G04, G07, G09, G11, G13, G15, and G18.

### Phase 02D — Final Data-Gate Closure

**Status:** BLOCKED by Phase 02B and external evidence.

Run all credentialed trials, coverage crawls, reconciliation panels, license reviews, and the final integrated Phase 02 audit. Phase 03 may start only if both the platform-foundation gate and all mandatory data gates pass.

---

# 3. Phase 02B — Mandatory Tasks

## P02-PF01 — TradeLead + Watchlist Domain Model

### Goal

Create the canonical object passed from the strategy/research layer to portfolio construction, UI, audit, and later execution planning.

### Required capabilities

A `TradeLead` must carry at minimum:

- immutable lead ID;
- internal instrument ID;
- historical/current symbol alias;
- strategy ID/version;
- generated/decision/valid-until timestamps;
- LONG/SHORT direction;
- score and component factors;
- trend and volatility state;
- universe eligibility state;
- rejection/block reasons;
- earnings/event state;
- spread/cost estimate state;
- borrow state for shorts;
- proposed portfolio weight/shares when applicable;
- dataset/universe/feature manifest hashes;
- lifecycle state and state-transition history.

Required lifecycle states:

`DISCOVERED -> WATCHLIST -> QUALIFIED -> RISK_REJECTED / EVENT_BLOCKED / COST_BLOCKED / BORROW_BLOCKED / PORTFOLIO_REJECTED -> PLANNED -> ENTERED -> EXIT_PENDING -> CLOSED / EXPIRED`

No lifecycle transition may alter the frozen strategy score retroactively.

### Acceptance

- deterministic state machine;
- explicit rejection reason codes;
- serialization round-trip;
- duplicate/idempotency tests;
- future-data/provenance tests;
- watchlist "what prevents qualification" derivation tests;
- no live-order side effects.

---

## P02-PF02 — Read-Only FastAPI + React Research Console

### Goal

Create the first user-facing application without introducing trading authority.

### Backend read models/endpoints

At minimum:

- `/overview`;
- `/leads`;
- `/watchlist`;
- `/portfolio`;
- `/risk`;
- `/research`;
- `/data-health`;
- `/phase-gates`;
- `/audit`;
- `/incidents`.

### UI screens

At minimum:

1. Command Center / Overview
2. Trade Leads
3. Watchlist
4. Research Portfolio
5. Risk Center
6. Research / Experiment Reports
7. Data Health
8. Phase Gates
9. Audit Trail
10. Incident Center

The UI must display qualification/rejection reasons and source/provenance details rather than generating post-hoc explanations.

### Hard safety boundary

Phase 02 UI is **read-only**.

Prohibited in this task:

- BUY/SELL/SUBMIT/CANCEL broker commands;
- live broker mutation endpoints;
- editing frozen strategy parameters from the browser;
- storing secrets in frontend code/local storage;
- claiming displayed fixture portfolios are live positions.

### Acceptance

- OpenAPI contract tests;
- API schema/DTO tests;
- frontend unit/component tests;
- fixture-driven integration tests;
- loading/empty/error states;
- accessibility/basic keyboard navigation checks;
- read-only authorization test proving no order mutation route exists.

---

## P02-PF03 — Event Model + Persistent Event Journal + Replay

### Goal

Introduce an auditable event backbone before broker/execution integration.

### Required event envelope

- event ID;
- event type;
- occurred-at;
- received-at;
- instrument/portfolio/strategy scope;
- correlation ID;
- causation ID;
- schema version;
- deterministic payload hash;
- source/provenance metadata.

Representative events:

- data snapshot accepted/rejected;
- universe refreshed;
- lead generated/blocked/expired;
- portfolio target generated;
- risk state changed;
- simulated order planned/submitted/accepted/filled/canceled;
- incident opened/resolved;
- reconciliation mismatch detected/resolved.

### Acceptance

- append-only journal;
- idempotent duplicate handling;
- deterministic replay from clean state;
- crash-safe persistence test;
- schema-version handling;
- correlation/causation chain validation;
- replay produces identical state hash.

---

## P02-PF04 — Runtime Safety State + Protection Framework

### Goal

Formalize operational safety independently from strategy alpha logic.

Required runtime states:

- `ACTIVE`;
- `REDUCING`;
- `HALTED`.

Protection framework must support scopes such as:

- strategy;
- instrument;
- portfolio;
- data subsystem;
- broker subsystem (simulated in Phase 02).

Initial protection implementations may include:

- stale-data guard;
- data-lineage/hash failure;
- portfolio concentration breach;
- daily/portfolio drawdown monitor as observational or operational safety only;
- reconciliation mismatch;
- unknown simulated order state.

### Governance boundary

Protection infrastructure may be implemented now. A protection that changes historical `CSMOM-LS-v0.2` alpha entry/exit rules cannot be activated in Phase 03 research without a separately recorded strategy decision.

### Acceptance

- deterministic transition table;
- `HALTED` cannot emit new-risk actions;
- `REDUCING` permits exposure reduction only;
- recovery requires explicit cleared condition;
- all transitions journaled and auditable.

---

## P02-PF05 — Lookahead + Recursive Strategy Validation Tools

### Goal

Add independent adversarial validation on top of existing PIT contracts.

### Lookahead validator

For historical decision time `t`, compare the result produced from the full dataset with a dataset truncated to only information legally available at `t`.

At minimum compare:

- universe membership;
- feature values;
- rankings;
- lead states;
- planned exits.

Required invariant:

`decision_full(t) == decision_truncated_at_t(t)`

except for explicitly documented nondeterminism, which is otherwise prohibited.

### Recursive/warm-up validator

Verify rolling indicators/signals do not materially change because excess future/earlier context or different warm-up lengths were supplied.

### Acceptance

- positive fixtures;
- deliberately contaminated fixtures that must fail;
- machine-readable violation report;
- CI-friendly non-zero exit on violation;
- strategy/dataset/version provenance in report.

---

## P02-PF06 — OMS State Machine + Simulated Broker

### Goal

Build the execution lifecycle safely before touching Schwab.

### Required order states

At minimum:

- `CREATED`;
- `RISK_APPROVED`;
- `SUBMITTING`;
- `SUBMITTED`;
- `ACKNOWLEDGED`;
- `PARTIALLY_FILLED`;
- `FILLED`;
- `CANCEL_PENDING`;
- `CANCELED`;
- `REJECTED`;
- `EXPIRED`;
- `UNKNOWN`;
- `RECONCILING`.

### SimulatedBroker requirements

- deterministic seeded fills;
- partial fills;
- rejects;
- cancel/replace simulation;
- network/ack uncertainty simulation;
- duplicate-submission protection;
- configurable latency/spread/slippage;
- no network access to a real broker.

### Acceptance

- legal/illegal transition tests;
- duplicate order/idempotency tests;
- `UNKNOWN` never blindly resubmits;
- partial-fill accounting tests;
- cancellation race tests;
- journal/replay parity.

---

## P02-PF07 — Deterministic Simulation Runtime (Future Paper-Compatible Skeleton)

### Goal

Prove that research signals, portfolio construction, risk, OMS, and position accounting can run through one common runtime interface.

This task is **not deployed paper trading**. It is an offline/synthetic simulation harness designed so a future paper adapter can replace `SimulatedBroker` without rewriting strategy/risk/OMS code.

### Acceptance

- deterministic clock;
- deterministic event ordering;
- same application services used by historical simulation and future broker adapters;
- restart/replay equivalence;
- no provider/broker credentials required;
- no network broker calls;
- no claim of paper/live readiness.

---

## P02-PF08 — Experiment Registry + Research Reporting + Attribution

### Goal

Make every future Phase 03 experiment reproducible and comparable.

### Experiment record

At minimum:

- experiment ID;
- strategy version;
- git commit;
- dataset/manifests;
- universe version;
- feature version;
- cost model version;
- borrow model version;
- parameters;
- acceptance/test interval;
- random seed where applicable;
- result hash;
- status and gate outcome.

### Reporting interfaces

Prepare the schema/UI for:

- equity curve;
- benchmark;
- drawdown/underwater;
- rolling risk metrics;
- monthly/yearly return tables;
- long vs short attribution;
- sector attribution;
- gross-to-net cost waterfall;
- spread/slippage/fees/borrow contribution;
- turnover/exposure;
- trade distribution;
- experiment comparison.

No profitability result may be populated or claimed before Phase 03.

### Acceptance

- experiment immutability/versioning tests;
- reproducible result hash;
- comparison API/UI with fixture data;
- report export test;
- explicit `SYNTHETIC/FIXTURE` badges for pre-Phase-03 results.

---

## P02-PF09 — Alert + Incident Center

### Goal

Create one operational surface for warnings and failures.

### Required severity

- INFO;
- WARNING;
- CRITICAL.

### Required capabilities

- open/deduplicate/update/resolve incident;
- source subsystem;
- instrument/portfolio scope;
- first-seen/last-seen timestamps;
- evidence links;
- related event IDs;
- runtime-state impact;
- acknowledgement metadata.

Initial incident types:

- stale/missing data;
- lineage/hash mismatch;
- blocked Phase gate;
- reconciliation mismatch;
- unknown simulated order state;
- borrow/event/corporate-action data exception;
- provider trial blocked.

### Acceptance

- deduplication tests;
- severity escalation tests;
- journal integration;
- UI filtering/acknowledgement;
- no external notification vendor required.

---

## P02-PF10 — Recovery + Reconciliation Simulation

### Goal

Prove that the platform fails safely across crashes, uncertain execution state, and local/external-state divergence before broker integration.

### Required simulations

- process crash after submission but before acknowledgement;
- missed partial fill;
- broker/simulated external order unknown locally;
- local order absent externally;
- position quantity mismatch;
- duplicate broker event;
- stale startup snapshot;
- journal replay after restart.

### Acceptance

- reconciliation detects all adversarial fixtures;
- unresolved mismatch forces `HALTED` or `REDUCING` per policy;
- recovery never creates duplicate risk;
- state is reconstructed deterministically;
- incident/audit records generated;
- no real broker required.

---

# 4. Phase 02B Integrated Acceptance Gate

Create gate `P02-PF-GATE`.

It receives **PASS** only when all P02-PF01 through P02-PF10 are PASS and the integrated validation suite proves:

1. a fixture market session can generate deterministic TradeLeads;
2. leads appear correctly in the read-only UI;
3. watchlist/rejection reasons match backend state;
4. a qualified lead can flow through portfolio/risk into the simulated OMS;
5. simulated fills update the research portfolio;
6. all state changes are journaled;
7. replay rebuilds an identical final state hash;
8. lookahead/recursive validators pass clean fixtures and fail contaminated fixtures;
9. runtime `HALTED` prevents new-risk simulated orders;
10. crash/reconciliation fixtures recover without duplicate risk;
11. experiment/reporting outputs are explicitly fixture/synthetic;
12. there are no live broker mutation endpoints or embedded commercial credentials.

## Procurement governance

Until `P02-PF-GATE = PASS`:

`PROCUREMENT_AUTHORIZED = false`

This means no Phase-02-motivated commercial account purchase should be made as part of the project plan. Free public-source research and vendor documentation review may continue, but paid subscriptions/licenses are deferred.

Passing this gate does **not** auto-purchase anything. It changes the state only to:

`PROCUREMENT_READY_FOR_MANUAL_APPROVAL = true`

---

# 5. Phase 02C — External Procurement and Evidence Sequence

After manual approval following P02-PF-GATE PASS, use the minimum-cost dependency order:

1. approve/configure compliant SEC monitored-contact User-Agent;
2. approve Databento/equivalent research retention terms and create account;
3. run PIT security-master + exact-execution representative panel;
4. generate real sector-blind target ledger;
5. run full SEC sector coverage crawl;
6. obtain written Kibot retention confirmation and purchase EOD access only if still needed by the accepted core stack;
7. run core provider representative-case trial;
8. obtain/approve WSH earnings-revision sample/license;
9. obtain/approve EDI corporate-action sample/license;
10. calibrate observed spreads, preferably reusing an already approved quote source;
11. obtain/approve historical borrow source or formally revisit the long/short acceptance policy if economics are disproportionate to the mandate;
12. rerun all 18 existing Phase 02 data gates.

No provider should be purchased merely because it appeared in an earlier candidate list. The latest accepted source/license decision controls.

---

# 6. Phase 02D — Final Exit Criteria

Phase 02 receives PASS only when all of the following are true:

- `P02-PF-GATE = PASS`;
- all 18 existing mandatory data gates = PASS;
- all licenses/retention rights used by the acceptance dataset are approved and recorded;
- all raw snapshots/manifests required for reproducibility are retained legally;
- final integrated PIT/leakage tests pass;
- all provider representative panels pass;
- no unresolved BLOCKED/CONDITIONAL Phase 02 gate exists;
- `PHASE03_AUTHORIZED` is changed by an explicit governance decision, not automatically by code.

---

# 7. Revised Phase 02 task order

| Order | Task | Current status | External account required? |
|---:|---|---|---|
| 1 | P02-PF01 TradeLead + Watchlist | NOT STARTED | No |
| 2 | P02-PF02 Read-only API + Research Console | NOT STARTED | No |
| 3 | P02-PF03 Event journal + replay | NOT STARTED | No |
| 4 | P02-PF04 Runtime safety/protections | NOT STARTED | No |
| 5 | P02-PF05 Lookahead/recursive validators | NOT STARTED | No |
| 6 | P02-PF06 OMS + SimulatedBroker | NOT STARTED | No |
| 7 | P02-PF07 Deterministic simulation runtime | NOT STARTED | No |
| 8 | P02-PF08 Experiment registry/reporting | NOT STARTED | No |
| 9 | P02-PF09 Alert/incident center | NOT STARTED | No |
| 10 | P02-PF10 Recovery/reconciliation simulation | NOT STARTED | No |
| 11 | P02-PF integrated acceptance | NOT STARTED | No |
| 12 | Procurement readiness review | BLOCKED BY PF GATE | No purchase yet |
| 13 | External accounts/licenses & credentialed trials | DEFERRED | Yes |
| 14 | Final Phase 02 audit | DEFERRED | Uses approved external evidence |
| 15 | Phase 03 authorization decision | PROHIBITED UNTIL PHASE 02 PASS | — |

---

# 8. Architecture target after Phase 02B

```text
                    Read-Only Research Console
                              |
                     REST / WebSocket Read API
                              |
                    Application / Read Models
                              |
              +---------------+----------------+
              |                                |
       Event Journal / Replay              Incident Center
              |
    +---------+---------+----------------+----------------+
    |                   |                |                |
 Data / PIT         Strategy          Portfolio          Risk
 Engines            TradeLeads       Construction       Protections
    |                   |                |                |
    +-------------------+----------------+----------------+
                              |
                          OMS Interface
                              |
                       SimulatedBroker

                NO LIVE BROKER IN PHASE 02B
```

This architecture is intentionally compatible with a later Schwab adapter without making Schwab a dependency of the current work.

---

# 9. Governance conclusion

**Decision:** Reshape Phase 02 by inserting the mandatory pre-purchase platform-foundation workstream described above.

Existing data gates and the frozen Phase 01 strategy remain unchanged.

The immediate next task is:

**P02-PF01 — TradeLead + Watchlist Domain Model.**

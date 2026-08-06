# Open Risk Register

## Rating scale

- Severity: Critical, High, Medium, Low
- Status: Open, Mitigating, Accepted, Closed

| ID | Risk | Category | Severity | Status | Current mitigation / next action |
|---|---|---|---|---|---|
| R-001 | Trading mandate is not approved | Governance | High | Open | Complete Phase 0 decisions before strategy or implementation work |
| R-002 | Account size and account type are unknown | Portfolio / broker | High | Open | Record capital and cash/margin constraints |
| R-003 | Broker and API capabilities are unknown | Execution | High | Open | Select broker only after mandate requirements are clear |
| R-004 | Point-in-time research data source is unknown | Data / statistics | Critical | Open | Define required history, membership, corporate actions, and timestamps in Phase 2 |
| R-005 | Risk thresholds are not approved | Risk | Critical | Open | Complete mandate discovery and freeze initial limits |
| R-006 | Laptop uptime and connectivity constraints are unknown | Operations | High | Open | Record operating window; prefer low-frequency mandate unless proven feasible |
| R-007 | Survivorship and look-ahead bias may invalidate results | Statistics | Critical | Open | Reconstruct historical universe or disclose and constrain conclusions |
| R-008 | Transaction costs and fills may consume apparent edge | Execution / statistics | Critical | Open | Use liquidity-sensitive costs and conservative execution scenarios |
| R-009 | Multiple testing may create false discoveries | Statistics | Critical | Open | Track every hypothesis and parameter experiment; protect final OOS |
| R-010 | Local and broker state may diverge | Operations / execution | Critical | Open | Design fail-closed reconciliation and broker-source-of-truth behavior |
| R-011 | Credentials could leak into research or logs | Security | Critical | Open | Separate environments and secret stores; test redaction |
| R-012 | Documentation may drift from implementation | Governance | Medium | Open | Require documentation review in every behavior-changing task |
| R-013 | Human overrides could silently alter strategy behavior | Governance / risk | High | Open | Require authenticated, reason-coded, append-only override logs |
| R-014 | Stops may execute far from planned prices during gaps | Market risk | High | Open | Model gap risk and cap overnight exposure |
| R-015 | Paper fills may overstate live execution quality | Execution | High | Open | Treat paper as integration evidence only and compare limited-live fills |

## Risk closure requirements

A risk is closed only when evidence, owner, decision, and residual risk are recorded. Passing a unit test alone does not close a statistical, market, or operational risk.

# Decision Register

This register is append-only. Superseded and rejected decisions remain visible.

## DEC-0001 — Master specification is governing authority

- Date: 2026-08-05
- Status: APPROVED
- Phase: Project initialization
- Context: The project requires durable instructions across ChatGPT, Codex, and repository work.
- Alternatives considered: Rely on chat history; paste a full prompt into every task; keep no formal governance record.
- Decision: Store the master specification in `docs/governance/MASTER_SPECIFICATION.md` and treat it as the governing authority.
- Rationale: Version-controlled documentation is reviewable, diffable, and independent of conversation context.
- Consequences: Material deviations require an explicit decision record.
- Risks introduced: Documentation can become stale if implementation changes are not reflected.
- Evidence required for reconsideration: A more reliable, versioned, auditable system of record.
- Supersedes: None
- Related files: `AGENTS.md`, `docs/project/CURRENT_STATE.md`

## DEC-0002 — Sequential phase delivery

- Date: 2026-08-05
- Status: APPROVED
- Phase: Project initialization
- Context: Premature implementation would embed unapproved assumptions and encourage backtest-driven requirement changes.
- Alternatives considered: Build the full application first; parallelize all phases immediately.
- Decision: Follow Phases 0 through 9 sequentially and implement only approved current-phase scope.
- Rationale: Phase gates protect statistical integrity and reduce architectural rework.
- Consequences: Progress may appear slower, but each stage has explicit evidence and exit criteria.
- Risks introduced: Over-documentation or analysis paralysis.
- Evidence required for reconsideration: A dependency that cannot be evaluated without a narrowly scoped later-phase prototype.
- Supersedes: None
- Related files: `docs/project/ROADMAP.md`

## DEC-0003 — Deterministic live trade path

- Date: 2026-08-05
- Status: APPROVED
- Phase: Project initialization
- Context: LLM output is non-deterministic and unsuitable as direct live-order authority.
- Alternatives considered: Allow an LLM to choose trades or override risk limits.
- Decision: Every live trading decision must come from deterministic, version-controlled code with recorded inputs. An LLM may assist research, explanation, diagnosis, and review only.
- Rationale: Reproducibility, testability, auditability, and operational safety.
- Consequences: No LLM-controlled live order submission, sizing, stop modification, or risk override.
- Risks introduced: Deterministic code can still contain defects and therefore requires independent testing and controls.
- Evidence required for reconsideration: None anticipated; this is a foundational safety constraint.
- Supersedes: None
- Related files: `docs/governance/RISK_POLICY.md`

## Decision template

### DEC-XXXX — Decision title

- Date:
- Status: PROPOSED | APPROVED | REJECTED | SUPERSEDED
- Phase:
- Decision owner:
- Context:
- Alternatives considered:
- Decision:
- Rationale:
- Assumptions:
- Consequences:
- Risks introduced:
- Evidence required for reconsideration:
- Supersedes:
- Related files or ADRs:

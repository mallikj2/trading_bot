# ADR-0001 — Version-Controlled Documentation as the System of Record

- Date: 2026-08-05
- Status: Accepted
- Decision owners: Project owner

## Context

The project will span many conversations, Codex tasks, experiments, and implementation phases. Conversation memory alone cannot reliably preserve approved mandates, frozen criteria, superseded decisions, open risks, or implementation state.

## Decision

Use repository Markdown documents as the authoritative, version-controlled system of record. ChatGPT and Codex must read the current state and applicable specifications before substantial work. Material decisions, state transitions, acceptance criteria, and unresolved risks must be committed.

## Alternatives considered

- Rely exclusively on a single long chat
- Paste the master prompt into every coding task
- Use undocumented local notes
- Allow implementation to become the only source of truth

## Consequences

Positive:

- Decisions are reviewable and diffable.
- ChatGPT and Codex can recover context across sessions.
- Acceptance criteria and protected evaluations have an audit trail.
- Documentation drift can be detected during review.

Negative:

- Documents require active maintenance.
- Conflicts between code and documents must be explicitly resolved.
- Excessive templates can slow work if not kept focused.

## Safety and failure modes

- Stale documentation can create incorrect implementation assumptions.
- Silent edits to frozen criteria can invalidate research integrity.
- A commit does not prove correctness; actual tests and evidence remain required.

## Validation

Every substantial task must identify the current phase, applicable documents, files changed, validation performed, and remaining risks.

## Related decisions and files

- `AGENTS.md`
- `docs/project/CURRENT_STATE.md`
- `docs/project/DECISIONS.md`
- `docs/project/ACCEPTANCE_CRITERIA.md`

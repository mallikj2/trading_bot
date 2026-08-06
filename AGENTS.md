# AGENTS.md — Quant Trading Platform

## Purpose

This repository implements a safety-critical personal algorithmic trading platform.
Capital preservation, deterministic behavior, reproducibility, reconciliation, and
fail-closed operation take priority over features and performance.

## Required reading

Before making substantial changes, read the documents relevant to the task:

1. `docs/governance/MASTER_SPECIFICATION.md`
2. `docs/project/CURRENT_STATE.md`
3. `docs/project/DECISIONS.md`
4. `docs/project/OPEN_RISKS.md`
5. The specification for the current phase in `docs/phases/`
6. Applicable architecture and data-contract documents

Do not assume that conversation history is authoritative when it conflicts with
version-controlled repository documentation.

## Phase discipline

- Work only on the phase identified in `docs/project/CURRENT_STATE.md`.
- Do not implement later-phase functionality unless it is an explicit prerequisite.
- Do not mark a phase complete without satisfying its recorded acceptance criteria.
- Preserve an untouched final out-of-sample dataset.
- Do not change pre-registered acceptance criteria after evaluating final results.
- Record material design decisions in `docs/project/DECISIONS.md` or an ADR.
- Record unresolved safety, statistical, execution, and operational risks.

## Trading safety

- Fail closed when critical data, broker state, risk state, persistence, or
  configuration is missing, stale, inconsistent, or unverifiable.
- Never allow an LLM-generated response to directly authorize, size, submit,
  replace, or cancel a live order.
- Keep research, backtest, paper, and live environments logically and physically separated.
- Treat the broker as authoritative for positions, orders, and fills.
- Never infer a fill from a timeout.
- All order submission paths must be idempotent and reconciliation-aware.
- Never bypass risk controls to recover losses.
- Do not place secrets in source code, logs, notebooks, tests, or committed configuration.

## Engineering rules

- Use typed Python and validate external inputs.
- Keep notebooks outside the production execution path.
- Add or update tests whenever behavior changes.
- Do not fabricate test results or claim commands were run when they were not.
- Use UTC internally for timestamps.
- Preserve immutable raw data.
- Maintain deterministic behavior for identical versioned inputs.
- Document illustrative code that is not production-ready.

## Before editing

Report briefly:

1. Current phase
2. Relevant requirements
3. Files expected to change
4. Tests or validation that will be performed
5. Any unresolved ambiguity that materially affects safety or correctness

## Before completion

- Run the applicable formatter, linter, type checker, and tests defined by the repository.
- Report commands actually run and their actual results.
- Update documentation when behavior or architecture changed.
- State any remaining failure modes or unverified assumptions.
- Do not declare PASS unless the recorded acceptance criteria are satisfied.

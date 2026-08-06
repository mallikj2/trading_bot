# AGENTS.md — Quant Trading Platform

## Purpose

This repository implements a safety-critical personal algorithmic trading platform. Capital preservation, deterministic behavior, reproducibility, reconciliation, and fail-closed operation take priority over features and performance.

## Required reading

Before making substantial changes, read the documents relevant to the task:

1. `docs/governance/MASTER_SPECIFICATION.md`
2. `docs/project/CURRENT_STATE.md`
3. `docs/project/DECISIONS.md`
4. `docs/project/ACCEPTANCE_CRITERIA.md`
5. `docs/project/OPEN_RISKS.md`
6. The current phase specification under `docs/phases/`
7. Applicable architecture and data-contract documents

Version-controlled repository documentation is authoritative when conversation history conflicts with it.

## Phase discipline

- Work only on the phase identified in `docs/project/CURRENT_STATE.md`.
- Do not implement later-phase functionality unless it is an explicit prerequisite.
- Do not mark a phase complete without satisfying its recorded acceptance criteria.
- Preserve an untouched final out-of-sample dataset.
- Do not change pre-registered acceptance criteria after protected evaluation begins.
- Record material decisions in `docs/project/DECISIONS.md` or an ADR.
- Record unresolved statistical, execution, operational, and security risks.

## Trading safety

- Fail closed when critical data, broker state, risk state, persistence, configuration, or time state is missing, stale, inconsistent, or unverifiable.
- Never allow an LLM response to directly authorize, size, submit, replace, or cancel a live order.
- Keep research, historical backtest, event simulation, paper, and live environments logically and physically separated.
- Treat the broker as authoritative for positions, orders, and fills.
- Never infer a fill from a timeout.
- Make order submission idempotent and reconciliation-aware.
- Never bypass risk controls to recover a loss.
- Never store secrets in source code, logs, notebooks, tests, committed configuration, or databases.

## Engineering rules

- Use typed Python and validate all external inputs.
- Keep notebook logic outside production execution paths.
- Add or update tests whenever behavior changes.
- Do not fabricate results or claim commands were run when they were not.
- Store timestamps in UTC internally.
- Preserve immutable raw data separately from normalized and derived data.
- Maintain deterministic behavior for identical versioned inputs.
- Label illustrative code that is not production-ready.

## Before editing

Report briefly:

1. Current phase
2. Applicable requirements
3. Files expected to change
4. Tests or validation to perform
5. Any ambiguity materially affecting safety or correctness

## Before completion

- Run applicable formatting, linting, type checking, and tests.
- Report only commands actually run and their actual results.
- Update documentation when behavior, contracts, risks, or architecture change.
- State remaining failure modes and unverified assumptions.
- Do not declare `PASS` unless recorded acceptance criteria are satisfied.

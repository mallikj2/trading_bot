# Phase 5 — Production Architecture

## Status

**NOT STARTED — blocked by earlier phases.**

## Objective

Design a modular local platform whose providers, brokers, strategies, and deployment environment can change without rewriting the core domain.

## Required outputs

- Component and data-flow architecture
- Typed domain models
- Repository structure
- Configuration and secret boundaries
- Persistence, migrations, and versioning strategy
- Research, simulation, paper, and live separation
- Unit, integration, simulation, and broker-contract test layers
- UTC and decimal-safe conventions

## Architectural rule

Notebook logic must not enter the production trade path. An LLM must not occupy a live decision boundary.

## Exit gate

Architecture must satisfy current strategy, risk, data, reconciliation, recovery, audit, and security requirements without speculative complexity.

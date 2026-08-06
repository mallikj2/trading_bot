# Phase 02 Minimum Data Kernel Architecture

**Kernel:** `PHASE02-MINIMUM-DATA-KERNEL-v0.1`  
**Strategy:** `CSMOM-LS-v0.2`  
**Status:** Implemented and locally validated

## Purpose

The kernel establishes the deterministic, point-in-time-safe boundary between provider adapters and later research/backtesting code. It does not fetch data, optimize a strategy, simulate fills, or authorize trading.

```text
Provider adapters
      |
      v
Immutable raw snapshot + source hashes
      |
      v
Typed contracts and validation
      |
      +--> instrument master / symbol aliases
      +--> exchange sessions
      +--> daily bars
      +--> corporate actions and revisions
      +--> PIT market cap / sectors / earnings records
      |
      v
Point-in-time selector
      |
      v
As-of adjustment and quality state
      |
      v
Frozen monthly universe + reason codes + lineage hashes
      |
      v
Phase 01 feature and strategy code (later integration)
```

## Modules

| Module | Responsibility |
|---|---|
| `contracts.py` | Frozen dataclasses and enums for bars, actions, identity, sessions, PIT observations, features, and universes |
| `hashing.py` | Canonical JSON and deterministic SHA-256 content hashing |
| `manifests.py` | Source-file descriptors, dataset manifests, immutable atomic writes, and hash verification |
| `pit.py` | Latest-known revision selection and feature-availability propagation |
| `identity.py` | Stable UUID instruments and effective-dated ticker aliases |
| `calendars.py` | Versioned exchange sessions, early-close-aware decisions, and monthly freeze timing |
| `corporate_actions.py` | As-of split/reverse-split price adjustment using only effective and available actions |
| `quality.py` | Deterministic bar dataset checks and raw dollar-volume primitive |
| `universe.py` | Exact Phase 01 monthly universe thresholds, complete reason codes, and deterministic membership hashing |
| `leakage.py` | Future-information scans and lineage-hash validation |

## Trust boundary

The kernel assumes provider-specific adapters preserve raw payloads and populate contract fields honestly. It verifies internal invariants and lineage, but it cannot establish that a provider's claimed historical coverage or timestamps are accurate. That remains part of the credentialed provider trial.

## Fail-closed principles

- No future record fallback.
- No naive datetimes.
- No ticker-only identity.
- No overwrite of raw files or manifests.
- No universe inclusion with missing sector, market cap, liquidity, history, or valid listing state.
- No retroactive application of a corporate action before it is effective and available.
- No dataset acceptance after a lineage or source-file hash mismatch.

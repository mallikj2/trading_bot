# Phase 01 v0.2 — Executed Test Results

**Strategy:** `CSMOM-LS-v0.2`  
**Execution date:** 2026-08-05  
**Result:** PASS

## Environment

- Python: Python 3.13.5
- NumPy: 2.3.5
- pandas: 2.2.3
- PyYAML: 6.0.3
- pytest: 9.0.2

## Commands executed

```bash
PYTHONPATH=src python -m pytest -q
python -m compileall -q src tests
```

## Output

```text
...................                                                      [100%]
19 passed in 7.85s
```

Python bytecode compilation also completed successfully with no reported errors.

## Material coverage

The executed suite includes non-vacuous tests for:

- exactly three long and three short candidates from a valid cross section;
- exact 12-minus-1 and 6-minus-1 momentum indexing;
- stable instrument-key and duplicate rejection;
- inclusive score boundaries and deterministic ties;
- most-negative-first short ranking;
- zero-MAD fail-closed behavior;
- future-data leakage resistance;
- input-order determinism;
- split-safe raw dollar volume;
- event/operational entry blocking and market-stress abstention;
- matched gross when one side is scarce;
- no target when one side is empty;
- whole-share net-exposure repair at USD 5,000;
- official-close-relative early-close timing;
- next-session target expiry;
- same-sector concentration limits;
- YAML/runtime configuration consistency.

These tests validate the focused Phase 01 reference module only. They do not constitute a backtest, profitability claim, broker validation, or live-trading authorization.

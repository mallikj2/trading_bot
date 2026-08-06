# Phase 01 v0.2 Repository Bundle

This bundle contains the corrected Phase 01 strategy research specification and focused reference implementation for `CSMOM-LS-v0.2`.

## Repository paths

- `docs/phases/PHASE_01_STRATEGY_RESEARCH_SPECIFICATION.md`
- `docs/phases/PHASE_01_THRESHOLD_REGISTRY.md`
- `docs/phases/PHASE_01_ACCEPTANCE_GATE.md`
- `docs/phases/PHASE_01_V0_1_REVIEW_FINDINGS.md`
- `docs/project/CURRENT_STATE_PHASE_01_PATCH.md`
- `docs/project/DECISIONS_PHASE_01_APPEND.md`
- `configs/strategies/csmom_ls_v0_2.yaml`
- `src/trading_bot/strategies/csmom_ls_v0_2.py`
- `tests/unit/strategies/test_csmom_ls_v0_2.py`
- `requirements-phase01.txt`
- `TEST_RESULTS.md`

## Local validation

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-phase01.txt
PYTHONPATH=src python -m pytest -q
```

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-phase01.txt
$env:PYTHONPATH = "src"
python -m pytest -q
```

## Merge guidance

1. Replace the unapproved v0.1 strategy/config/test files with v0.2 or retain v0.1 only as historical evidence.
2. Merge the current-state patch into the canonical `docs/project/CURRENT_STATE.md`.
3. Append the decision entries to canonical `docs/project/DECISIONS.md`.
4. Do not mark Phase 01 PASS until the owner records `APPROVE STRATEGY SPEC V0.2`.
5. Do not authorize any broker order from this bundle.

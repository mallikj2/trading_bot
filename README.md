# Phase 02 Minimum Data Kernel Bundle

This is an incremental repository bundle for the Quant Trading Bot project.

## Merge destination

Copy the bundle contents into the repository root. It adds files under:

```text
src/trading_bot/data/
tests/unit/data/
tests/integration/data/
configs/data/
docs/data/
docs/phases/
docs/project/
```

It does not replace the approved Phase 01 strategy implementation or the earlier Phase 02 reconciliation/provider-PoC files.

## Validate

From the repository root:

```bash
python -m unittest discover -s tests/unit/data -p 'test_*.py' -v
python -m unittest discover -s tests/integration/data -p 'test_*.py' -v
python -m compileall -q src tests
```

## Import example

```python
from trading_bot.data.manifests import DatasetManifest
from trading_bot.data.pit import select_latest_known
from trading_bot.data.universe import build_monthly_universe
```

Ensure `src` is on `PYTHONPATH`, or install the repository package in the normal project environment.

## Status

- Minimum data-kernel task: PASS.
- Phase 02 overall: ACTIVE.
- Phase 03, paper trading, and live trading: not authorized.

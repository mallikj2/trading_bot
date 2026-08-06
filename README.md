# Phase 02 Production Provider Adapters

This incremental repository bundle adds production-oriented Massive and SEC ingestion above the approved Phase 02 minimum data kernel.

## Run local validation

```bash
PYTHONPATH=src python -m unittest discover -s tests/unit/data/adapters -p 'test_*.py' -v
PYTHONPATH=src python -m unittest discover -s tests/integration/data/adapters -p 'test_*.py' -v
PYTHONPATH=src python -m compileall -q src tests
```

## Check credential readiness

```bash
PYTHONPATH=src python -m trading_bot.data.adapters.trial environment-status
```

## Run smoke trial

```bash
export MASSIVE_API_KEY='...'
export SEC_USER_AGENT='QuantTradingBot/0.2 monitored-contact@example.com'
PYTHONPATH=src python -m trading_bot.data.adapters.trial smoke --output artifacts/provider_trial/smoke.json
```

No credentials or licensed data are included in this bundle.

# PF08 Experiment Registry + Reporting

PF08 adds immutable synthetic experiment lineage, result hashes, long/short and cost attribution, baseline scenario comparison, a GET-only `/api/v1/experiments` endpoint, and an Experiments page in the Research Console.

All committed PF08 metrics are synthetic fixtures labeled `NOT_STRATEGY_EVIDENCE`. They do not prove or disprove strategy profitability.

Local fixture verification:

```bash
PYTHONPATH=src python -m trading_bot.platform.experiment_cli \
  --registry /tmp/pf08.sqlite \
  --output /tmp/pf08.json
```

# PF05 Strategy Validation

P02-PF05 adds deterministic lookahead and recursive-stability analysis for CSMOM-LS-v0.2.

Primary entry points:

```bash
python -m trading_bot.platform.validation_cli lookahead --csv research_panel.csv --decision-date YYYY-MM-DD
python -m trading_bot.platform.validation_cli recursive --csv research_panel.csv --decision-date YYYY-MM-DD --warmup 300 --warmup 320 --warmup 360
python -m trading_bot.platform.validation_cli suite --csv research_panel.csv --decision-date YYYY-MM-DD
```

The CSV must conform to the frozen CSMOM strategy input contract. These commands are research validators only; they submit no orders and require no broker credentials.

See:

- `docs/platform/LOOKAHEAD_RECURSIVE_VALIDATION_CONTRACT.md`
- `docs/phases/PHASE_02_PF05_LOOKAHEAD_RECURSIVE_VALIDATION.md`
- `PF05_STRATEGY_VALIDATION_RESULTS.json`

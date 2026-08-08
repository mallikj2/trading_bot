# PF03 Event Journal + Replay

New local platform foundation:

```text
DomainEvent
    ↓
SQLiteEventJournal
    ↓
append-only sequence + SHA-256 chain
    ↓
ReplayEngine
    ↓
TradeLeadProjector
    ↓
canonical projection + state hash
```

Quick local replay:

```bash
PYTHONPATH=src python -m trading_bot.platform.replay_cli var/event_journal/platform_events.sqlite3
```

Runtime journal files under `var/` are local operational artifacts and should not be committed. The source/config/tests contain no broker or commercial-data credentials.

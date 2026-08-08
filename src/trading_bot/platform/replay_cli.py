"""Command-line integrity/replay utility for PF03 local journals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.replay import ReplayEngine, TradeLeadProjector


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify and deterministically replay a PF03 event journal")
    parser.add_argument("journal", type=Path, help="Path to SQLite event journal")
    parser.add_argument("--through-sequence", type=int, default=None)
    args = parser.parse_args(argv)

    with SQLiteEventJournal(args.journal) as journal:
        head = journal.verify_integrity()
        result = ReplayEngine(TradeLeadProjector()).replay_journal(
            journal, through_sequence=args.through_sequence
        )
    output = result.to_dict()
    output["verified_journal_head_hash"] = head
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

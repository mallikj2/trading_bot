"""CLI for deterministic PF07 simulation plans."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.simulation_runtime import SimulationRuntime, load_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a deterministic synthetic trading session")
    parser.add_argument("plan")
    parser.add_argument("journal")
    parser.add_argument("--through-ordinal", type=int)
    parser.add_argument("--result")
    args = parser.parse_args()
    plan = load_plan(args.plan)
    journal = SQLiteEventJournal(args.journal)
    try:
        result = SimulationRuntime(journal=journal).run(plan, through_ordinal=args.through_ordinal)
    finally:
        journal.close()
    payload = json.dumps(result.to_dict(), indent=2, sort_keys=True)
    if args.result:
        Path(args.result).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

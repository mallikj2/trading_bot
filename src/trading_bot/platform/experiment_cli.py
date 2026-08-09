"""Local PF08 fixture registry/report command. No provider/broker access."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from trading_bot.platform.experiments import ExperimentDefinition, ExperimentRun, SQLiteExperimentRegistry, build_pf08_fixture_report


def main() -> int:
    parser=argparse.ArgumentParser(description="Build/verify PF08 synthetic experiment registry")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output", required=True)
    args=parser.parse_args()
    report=build_pf08_fixture_report(as_of=datetime(2026,8,8,20,30,tzinfo=timezone.utc))
    with SQLiteExperimentRegistry(args.registry) as registry:
        for row in report["experiments"]:
            registry.register_definition(ExperimentDefinition.from_dict(row["definition"]))
            registry.register_run(ExperimentRun.from_dict(row["run"]))
        verification=registry.verify()
    payload={"task":"P02-PF08","status":"PASS","registry_verification":verification,"report":report}
    Path(args.output).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations
import argparse
import json
from trading_bot.platform.pre_purchase_gate import run_pre_purchase_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P02-PF-GATE integrated pre-purchase validation")
    parser.add_argument("repo_root", nargs="?", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_pre_purchase_gate(args.repo_root).to_dict()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

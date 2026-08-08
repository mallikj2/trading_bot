# P02-G07 SEC Sector Coverage Runbook

## Prerequisites

1. Produce the sector-blind PIT target ledger from the historical universe stack.
2. Set a compliant SEC User-Agent containing a real monitored contact email.
3. Use a persistent local raw-data root and working checkpoint path.

Environment example:

```bash
export SEC_USER_AGENT='QuantTradingBot YourMonitoredEmail@example.com'
export SEC_SECTOR_TARGET_LEDGER='/path/to/sector_blind_target_ledger.json'
```

Do not commit the real email address to source control.

## Run

```bash
PYTHONPATH=src python -m trading_bot.data.adapters.sec_sector_crawl \
  --targets "$SEC_SECTOR_TARGET_LEDGER" \
  --reviews data/research/sector_change_reviews.csv \
  --raw-root data/research/raw \
  --checkpoint data/research/working/sec_sector_coverage_checkpoint.json \
  --output SEC_SECTOR_COVERAGE_RESULTS.json
```

The crawler defaults to 5 requests/second, below the SEC's stated 10 requests/second maximum.

## First pass

The first run may return BLOCKED because manual reviews have not yet been completed even if automated coverage exceeds 99%.

Generate/complete at least 25 real detected sector-change review rows using original SEC archive evidence. Review should include a mix of legacy and modern filings and multiple FF12 sectors.

## Acceptance

Re-run with the completed review file. P02-G07 is eligible for PASS only when the machine result reports:

```text
coverage_ratio >= 0.99
unresolved_filing_count = 0
interval_overlap_count = 0
traceable_sector_change_count = sector_change_count
approved_manual_reviews >= 25
rejected_manual_reviews = 0
```

## Failure handling

Do not repair coverage by copying a later sector backward.

For a removed current filing, recover historical content from the corresponding original SEC daily archive/Oldloads evidence. If recovery cannot be completed, affected decision points remain missing and block the gate.

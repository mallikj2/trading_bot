# Provider Trial Runbook

## 1. Safety and environment

Run only in the isolated research environment. Do not place broker credentials in this environment.

Required environment variables:

```powershell
$env:MASSIVE_API_KEY = "..."
$env:SEC_USER_AGENT = "QuantTradingBot your-email@example.com"
```

Do not commit either value.

## 2. Local fixture validation

From the repository root:

```powershell
python -m unittest discover -s tests/unit/data -p "test_provider_poc.py" -v
python -m src.data.provider_poc.cli validate-fixtures `
  --fixture-root tests/fixtures/provider_poc
```

Expected result: all local contract tests pass.

## 3. Massive credential smoke test

```powershell
python -m src.data.provider_poc.cli massive-smoke `
  --as-of-date 2024-11-29 `
  --symbols AAPL,META,ELV,PARA,XYZ `
  --output data/research/raw/massive/provider_poc
```

The command must save raw payloads before normalization and generate SHA-256 hashes. It is only the active-universe smoke test.

For every delisted candidate, first identify its last active session from provider evidence, then rerun the command with that historical `--as-of-date`. Separately verify that no tradable bars appear after the terminal session. Do not query all delisted symbols using one current date and interpret missing current records as failed historical coverage.

## 4. Massive intraday window test

```powershell
python -m src.data.provider_poc.cli massive-window `
  --symbol AAPL `
  --session-date 2024-11-29 `
  --output data/research/raw/massive/provider_poc
```

Repeat for:

- a normal session;
- an early-close session;
- a missing/zero-volume case;
- a symbol near a corporate action.

## 5. SEC enrichment test

```powershell
python -m src.data.provider_poc.cli sec-smoke `
  --cik 0000320193 `
  --decision-at 2024-07-31T20:30:00Z `
  --output data/research/raw/sec/provider_poc
```

Required checks:

- response uses the declared user agent;
- request rate remains below SEC limits;
- raw JSON is immutable;
- selected shares fact was accepted no later than the decision timestamp;
- later filings do not alter the selected historical result;
- SIC is read from a filing accepted no later than the decision timestamp.

## 6. Earnings revision sample

Request a machine-readable WSH DateBreaks sample covering at least 20 issuers and 12 months, including:

- initial inferred date;
- tentative date;
- confirmed date;
- revision/cancellation;
- event time classification;
- message or known-at timestamp.

Save the original file under:

```text
data/research/raw/wsh/datebreaks/{retrieval_date}/{snapshot_id}/
```

Then map it into the `earnings_revisions.json` contract and run the fixture validator.

## 7. Required output

The credentialed run must produce:

```text
docs/data/PROVIDER_POC_CREDENTIALED_RESULTS.md
data/research/manifests/provider_poc_manifest.json
data/research/quality/provider_poc_quality_report.json
```

Every claim must identify:

- provider plan;
- retrieval timestamp;
- request parameters;
- raw file hash;
- adapter version;
- schema version;
- pass/fail evidence;
- unresolved discrepancies.

## 8. Stop conditions

Stop and mark the trial FAIL when:

- point-in-time ticker queries change historical identifiers unpredictably;
- delisted histories are absent or truncated;
- raw and adjusted price semantics cannot be reconciled;
- minute bars omit expected valid intervals without an explainable halt;
- license terms prohibit required local retention;
- an API silently returns current fundamentals for historical dates;
- earnings records contain no known-at/revision sequence;
- any test requires future information.

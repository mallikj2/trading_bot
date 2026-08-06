# Validation Results

**Bundle:** Phase 02 Provider Proof of Concept  
**Validated:** 2026-08-05  
**Result:** PASS for local contracts and synthetic fixtures; credentialed provider evidence remains pending

## Scope boundary

These tests validate deterministic code paths, fail-closed contracts, schemas, and synthetic adversarial fixtures. They do **not** demonstrate licensed-provider coverage, accuracy, retention rights, earnings-revision history, or spread calibration.

## Unit tests

Command:

```bash
python -m unittest discover -s tests/unit/data -p 'test_provider_poc.py' -v
```

Output:

```text
test_complete_vwap_window (test_provider_poc.ProviderPocTests.test_complete_vwap_window) ... ok
test_current_only_earnings_calendar_fails (test_provider_poc.ProviderPocTests.test_current_only_earnings_calendar_fails) ... ok
test_earnings_revision_sequence_passes (test_provider_poc.ProviderPocTests.test_earnings_revision_sequence_passes) ... ok
test_future_pit_record_is_invisible (test_provider_poc.ProviderPocTests.test_future_pit_record_is_invisible) ... ok
test_incomplete_vwap_window_fails (test_provider_poc.ProviderPocTests.test_incomplete_vwap_window_fails) ... ok
test_latest_known_pit_revision_is_selected (test_provider_poc.ProviderPocTests.test_latest_known_pit_revision_is_selected) ... ok
test_no_known_pit_record_fails (test_provider_poc.ProviderPocTests.test_no_known_pit_record_fails) ... ok
test_spread_proxy_has_floor (test_provider_poc.ProviderPocTests.test_spread_proxy_has_floor) ... ok
test_spread_proxy_is_deterministic (test_provider_poc.ProviderPocTests.test_spread_proxy_is_deterministic) ... ok
test_spread_proxy_rejects_invalid_bar (test_provider_poc.ProviderPocTests.test_spread_proxy_rejects_invalid_bar) ... ok
test_ticker_snapshot_passes (test_provider_poc.ProviderPocTests.test_ticker_snapshot_passes) ... ok
test_ticker_snapshot_rejects_non_common_stock (test_provider_poc.ProviderPocTests.test_ticker_snapshot_rejects_non_common_stock) ... ok
test_ticker_snapshot_requires_stable_identity (test_provider_poc.ProviderPocTests.test_ticker_snapshot_requires_stable_identity) ... ok
test_zero_volume_vwap_window_fails (test_provider_poc.ProviderPocTests.test_zero_volume_vwap_window_fails) ... ok

----------------------------------------------------------------------
Ran 14 tests in 0.002s

OK
```

## Fixture validator

Command:

```bash
python -m src.data.provider_poc.cli validate-fixtures --fixture-root tests/fixtures/provider_poc
```

Output:

```json
{
  "status": "PASS",
  "vwap": 100.13666666666667
}
```

## Compilation

Command:

```bash
python -m compileall -q src tests
```

Result: PASS; no compilation errors.

## Configuration and fixture parsing

```text
PASS JSON tests/fixtures/provider_poc/earnings_revisions.json
PASS JSON tests/fixtures/provider_poc/intraday_complete.json
PASS JSON tests/fixtures/provider_poc/intraday_incomplete.json
PASS JSON tests/fixtures/provider_poc/pit_records.json
PASS JSON tests/fixtures/provider_poc/ticker_snapshot.json
PASS YAML configs/data/provider_poc.yaml
```

## Verified local behaviors

- Rejects non-common-stock universe rows.
- Requires at least one stable identity field.
- Rejects duplicate ticker/identity rows.
- Rejects incomplete 10:00–10:30 ET VWAP windows.
- Rejects zero-volume VWAP intervals.
- Prevents future point-in-time revisions from being selected.
- Selects the latest revision known at the decision timestamp.
- Rejects current-only earnings calendars without a revision sequence.
- Produces deterministic modeled spread output and rejects invalid bars.
- Prevents overwrite of raw adapter snapshots.

## Outstanding evidence

- Massive Developer credentialed API/flat-file trial.
- Representative delisting, symbol-change, corporate-action, and ten-year coverage tests.
- SEC filing/accession joining for historical acceptance timestamps and security-class shares.
- Written provider-license retention review.
- Wall Street Horizon DateBreaks sample and quote.
- Calibration of the historical spread proxy against observed consolidated quotes.

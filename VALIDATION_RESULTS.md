# Validation Results

**Bundle:** Phase 02 Minimum Data Kernel  
**Validated:** 2026-08-05  
**Task result:** PASS  
**Phase 02 result:** ACTIVE — outstanding external-data gates remain

## Scope boundary

The validation proves the local deterministic data contracts, immutable storage behavior, point-in-time selection, identity rules, calendar rules, split-adjustment behavior, monthly-universe policy, leakage checks, and reproducible hashes.

It does not prove provider coverage, provider timestamp accuracy, license rights, earnings-revision availability, quote-based spread calibration, short borrow history, or strategy performance.

## Unit tests

Command:

```bash
python -m unittest discover -s tests/unit/data -p 'test_*.py' -v
```

Result:

```text
Ran 38 tests
OK
```

Validated behaviors include:

- timezone-aware UTC normalization and naive-datetime rejection;
- OHLC, volume, revision, and feature-lineage invariants;
- daily bars cannot be available before observation;
- raw snapshot and manifest overwrite rejection;
- source-file mutation detection by SHA-256;
- manifest lineage hash reproducibility independent of storage ID;
- no future revision fallback;
- conflict rejection for equal PIT revision keys;
- symbol change preservation and non-overlapping ticker reuse;
- rejection of overlapping ticker ownership;
- identity aliases unavailable at the decision time are invisible;
- regular sessions, early closes, next-session lookup, and monthly freeze time;
- future and unavailable corporate actions do not adjust prices;
- latest known corporate-action revision is selected;
- conflicting action revisions fail closed;
- exact Phase 01 universe boundaries are inclusive;
- every applicable universe rejection reason is retained;
- future-information and lineage-hash leakage checks;
- order-invariant universe membership hashes.

## Integration test

Command:

```bash
python -m unittest discover -s tests/integration/data -p 'test_*.py' -v
```

Result:

```text
Ran 1 test
OK
```

The integration test builds a source-file manifest, verifies the raw hash, freezes a monthly universe twice, and confirms identical manifest and universe lineage hashes.

## Approved Phase 01 merge regression

The minimum kernel was overlaid on the approved `phase01_v0_2_repo_bundle`.

Commands:

```bash
PYTHONPATH=src pytest -q tests/unit/strategies/test_csmom_ls_v0_2.py
PYTHONPATH=src python -m unittest discover -s tests/unit/data -p 'test_*.py' -v
PYTHONPATH=src python -m unittest discover -s tests/integration/data -p 'test_*.py' -v
```

Results:

```text
19 Phase 01 strategy tests passed
38 Phase 02 kernel unit tests passed
1 Phase 02 kernel integration test passed
```

No approved Phase 01 regression was detected.

## Compilation

Command:

```bash
python -m compileall -q src tests
```

Result: PASS; no compilation errors.

## Configuration parsing

Command:

```bash
python - <<'PY'
from pathlib import Path
import yaml
path = Path('configs/data/minimum_data_kernel.yaml')
payload = yaml.safe_load(path.read_text(encoding='utf-8'))
assert payload['kernel']['id'] == 'PHASE02-MINIMUM-DATA-KERNEL-v0.1'
print('PASS')
PY
```

Result: PASS.

## Remaining Phase 02 evidence

- Credentialed Massive trial and representative historical cases.
- Provider retention-license review.
- SEC production adapter and share-class mapping.
- Formal sector-taxonomy approval.
- Revision-aware historical earnings feed.
- Production VWAP normalization.
- Historical spread calibration.
- Conservative short-borrow model.
- Complex corporate-action and total-return processing.

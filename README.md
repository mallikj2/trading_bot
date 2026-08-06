# Phase 02 Provider Proof-of-Concept Bundle

This bundle contains the incremental repository files for the Phase 02 provider proof-of-concept task.

## Contents

- Provider decision and gate report
- Provider capability matrix and official evidence register
- Credentialed trial runbook and results template
- Historical spread proxy candidate
- Machine-readable provider PoC configuration
- Massive and SEC read-only adapter skeletons
- Fail-closed validators
- Adversarial fixtures and unit tests
- Current-state and decision-log patches

## Validation

Run:

```bash
python -m unittest discover -s tests/unit/data -p 'test_provider_poc.py' -v
python -m src.data.provider_poc.cli validate-fixtures --fixture-root tests/fixtures/provider_poc
```

No paid-provider data is included. The fixture payloads are synthetic schema examples and must not be represented as provider evidence.

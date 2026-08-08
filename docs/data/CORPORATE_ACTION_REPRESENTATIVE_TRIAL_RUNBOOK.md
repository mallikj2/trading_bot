# Corporate-Action Representative Trial Runbook

**Gate:** P02-G09  
**Result required:** PASS before Phase 03

## Purpose

Reconcile the Phase 02 corporate-action/total-return engine against independent licensed provider records while preserving point-in-time revisions and immutable raw evidence.

## Inputs

Required environment/configuration:

```text
EDI_CORPORATE_ACTIONS_EXPORT_PATH=<approved raw JSON/CSV export>
EDI_CORPORATE_ACTIONS_LICENSE_APPROVED=true
DATABENTO_API_KEY=<secret>
DATABENTO_CORPORATE_ACTIONS_LICENSE_APPROVED=true
```

EDI authentication is intentionally not encoded from public examples. Obtain the representative export using the authentication/entitlement instructions supplied with the executed EDI trial agreement, then preserve the raw file unchanged.

## EDI staging rule

For the finite representative trial, an operator-side staging copy may add:

- `case_id` or `_case_id` — link to a golden case;
- `ratio_semantics` — `TOTAL_NEW_OVER_OLD` or `ADDITIONAL_NEW_OVER_OLD` only when confirmed from the provider field contract;
- `source_snapshot_id`.

The raw source export must remain immutable alongside the staging copy. Do not rewrite the raw provider record.

## Command

```bash
PYTHONPATH=src python -m trading_bot.data.adapters.corporate_action_trial \
  --golden-cases tests/fixtures/data/corporate_action_provider_golden_cases.json \
  --output CORPORATE_ACTION_PROVIDER_TRIAL_RESULTS.json
```

## Mandatory cases

1. NVDA 2024 forward split.
2. GE 2021 reverse split.
3. IBM/Kyndryl 2021 spinoff.
4. Xilinx/AMD 2022 stock acquisition.
5. Twitter 2022 cash merger.
6. Bed Bath & Beyond 2023 bankruptcy/zero recovery.

## Mandatory checks

For each relevant provider record:

- stable provider event ID exists;
- listing/security identity is independently resolved;
- effective/ex date agrees with official economics;
- the latest record at the reconciliation cut-off is selected;
- future revisions are invisible;
- cancellation/deletion records are retained;
- equal latest conflicting revisions block;
- multiple distinct same-day candidate events block;
- split/reverse-split ratio reconciles;
- spinoff distribution ratio and outturn identifier exist;
- stock merger exchange ratio and successor identifier exist;
- cash consideration and currency reconcile;
- terminal zero recovery is explicit rather than inferred.

## Coverage checks after representative cases

The paid/trial sample must also answer:

- earliest usable US-equity history;
- frequency of missing stable identifiers;
- frequency of missing effective/ex dates;
- revision/cancellation availability;
- complex-event coverage by type;
- delisted/bankrupt security coverage;
- documented retention/non-display rights under the executed agreement.

## Pass rule

P02-G09 may be changed to PASS only when:

1. all six representative cases pass EDI reconciliation;
2. all six recent cases that fall in Databento's history pass the PIT overlap cross-check or have a documented provider-specific non-applicability reason approved in the decision log;
3. raw evidence is hashed and retained;
4. the actual EDI and Databento account/order terms needed for the test have been approved;
5. no unresolved action-economics or identity ambiguity remains.

A partial or unavailable provider result remains BLOCKED; it is not converted to PASS by a synthetic fixture.

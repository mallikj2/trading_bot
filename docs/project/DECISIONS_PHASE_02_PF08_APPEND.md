# Decision Log Append — P02-PF08

## D02-PF08-01 — Experiment provenance is mandatory before metrics

Accepted. Strategy/code/data/universe/parameter/cost-model lineage is part of experiment identity; orphan performance metrics are not valid experiment evidence.

## D02-PF08-02 — Registry records are append-only

Accepted. Experiment definitions and runs cannot be updated or deleted. Corrections require new content-addressed records.

## D02-PF08-03 — Result hashes are independent from run identity

Accepted. Metrics, attribution, and artifacts produce a deterministic `result_hash`; the run identity then binds that result to definition, evidence class, timing, and runtime hash.

## D02-PF08-04 — PF08 cannot create Phase 03 acceptance evidence

Accepted. `PHASE03_ACCEPTANCE` evidence is rejected in the PF08 domain model. Synthetic fixture reporting cannot authorize Phase 03 or support profitability claims.

## D02-PF08-05 — Attribution must reconcile exactly

Accepted. Net result must equal long contribution + short contribution + all cost components. Positive cost components and mismatches fail closed.

## D02-PF08-06 — Reporting compares; it does not optimize

Accepted. Baseline-relative deltas are allowed. Automatic winner/parameter selection is prohibited before preregistered Phase 03 research governance.

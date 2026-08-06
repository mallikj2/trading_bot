# Phase 02 Historical Sector Classification Bundle

Repository-ready incremental bundle for the Phase 02 historical sector task.

## Apply after

- Phase 01 v0.2 approved strategy bundle;
- Phase 02 minimum data kernel;
- Phase 02 production provider adapters.

## Contents

- SEC Archives text transport and complete-submission client;
- filing-header SIC parser for legacy SGML and modern EDGAR headers;
- frozen Fama–French 12-sector mapping;
- point-in-time sector interval builder and selector;
- adversarial unit and universe-integration tests;
- source evaluation, data contract, phase report, configuration, and project patches.

## Validation

See `VALIDATION_RESULTS.md`.

## Important limitation

This package does not claim full-universe SEC sector coverage. Run the configured coverage gate with a compliant `SEC_USER_AGENT` containing a real monitored contact email before final Phase 02 approval.

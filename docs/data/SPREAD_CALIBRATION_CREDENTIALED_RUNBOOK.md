# Credentialed Historical Spread Calibration Runbook

## Preconditions

Do not run the paid quote trial until all are true:

- exact historical quote provider and dataset selected;
- explicit approval for the historical quote-data spend;
- internal non-display research, caching/export, local archival, and post-termination/post-download rights approved and recorded;
- provider credentials are supplied through environment secrets only;
- the acceptance-period start is frozen;
- point-in-time universe, ADV60, identity and daily bars are available.

## Deterministic sample

For each weekly entry decision and ADV60 bucket:

1. enumerate point-in-time eligible instruments;
2. compute SHA-256 of `instrument_id | decision_session_date | calibration_version`;
3. take the 10 lowest hashes per bucket;
4. persist the selection manifest before requesting quotes.

Never replace an inconvenient sampled name after viewing its spread.

## Quote window

For each sampled instrument, retrieve enough historical NBBO data to establish the prevailing state at 10:00 ET and all quote changes through 10:30 ET on the strategy's next execution session.

Persist raw provider pages immutably, including request parameters, pagination lineage, retrieval time and SHA-256 hashes.

## Validation

For every window:

- complete bid and ask required;
- crossed market rejects the observation;
- first prevailing quote age <= 60 seconds;
- participant and SIP timestamps must be ordered;
- duplicate sequence numbers reject the window;
- time-weighted spread must cover the full 1,800 seconds;
- source snapshot ids must be recorded.

## Walk-forward calibration

At each historical model fit:

- use only targets with `available_at <= fit_at`;
- require >= 500 observations per ADV60 bucket;
- calculate robust bucket medians exactly as specified in the spread contract;
- store model fit timestamp, counts, medians, version and lineage hash;
- no refitting based on strategy P&L is permitted.

## Acceptance report

Report:

- requested and successful windows by year/bucket;
- rejected windows by reason;
- coverage percentage;
- raw proxy vs observed spread median/MAE by bucket;
- calibrated prediction vs observed spread median/MAE by bucket;
- percentage of historical decisions blocked at >35 bps;
- any years/buckets without sufficient calibration evidence;
- provider/dataset identifier, exact license approval reference, and acquisition-cost evidence.

## Gate

A missing bucket, unapproved retention right, or future-leaking calibration point prevents Phase 02 spread-gate closure.


Massive public Individual Market Data Terms are not sufficient authorization for this runbook. Massive may be used only if a separate written license has been approved.

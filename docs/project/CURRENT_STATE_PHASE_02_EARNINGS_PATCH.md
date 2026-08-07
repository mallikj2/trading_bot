# CURRENT_STATE.md — Phase 02 Earnings Schedule Patch

Apply after the Phase 02 corporate-action/total-return patch.

## Active phase

**Phase 02 — Data and Point-in-Time Design**

## Newly completed

- Revision-aware historical earnings schedule contract implemented.
- Immutable schedule versions preserve event date, BMO/AMC/during/unknown timing, status, source availability, and lineage.
- Explicit forward-calendar coverage prevents "no row" from being treated as "no earnings".
- Phase 01 10-session entry exclusion is implemented point-in-time.
- BMO/unknown/during-session prior-session exits and AMC event-session exits are implemented.
- Withdrawn/unresolved schedules fail closed.
- Late schedule changes create operational exceptions and next-available exits; history is not rewritten.
- Wall Street Horizon DateBreaks + Earnings Date Daily Snapshots selected as the preferred historical source candidate, pending trial and license.
- Massive/Benzinga retained for development/corroboration only unless prior-version retrieval is proven.
- Intrinio Corporate Events rejected as the sole historical source because current product documentation says history is most recent only.

## Conditional evidence

No licensed historical earnings source has yet passed the representative-case trial. Wall Street Horizon pricing, schema, exact identifiers, completeness, and local/post-termination retention rights remain unverified.

## Phase 02 remains active

Open blockers and conditions:

1. credentialed provider representative-case evidence;
2. provider storage/retention license approval;
3. Wall Street Horizon earnings historical sample and coverage evidence;
4. full SEC historical-sector coverage evidence;
5. provider complex-action/terminal-value reconciliation;
6. historical spread calibration;
7. short-borrow model;
8. final Phase 02 acceptance gate.

## Authorization state

- Phase 03 final acceptance backtest: not authorized.
- Paper trading: not authorized.
- Limited live trading: not authorized.
- Live shorting: prohibited.

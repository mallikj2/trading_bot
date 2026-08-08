# SEC Filing-Header SIC Contract

**Contract version:** 0.1.0

## Raw record

Each accepted record contains:

- stable `instrument_id`;
- zero-padded filer or subject-company CIK;
- accession number;
- filing form;
- four-digit non-zero assigned SIC;
- optional SIC description;
- exact EDGAR acceptance timestamp;
- conservative availability timestamp;
- immutable raw snapshot ID;
- amendment revision indicator.

## Identity rules

1. The parser selects the entity block whose CIK exactly matches the requested target CIK.
2. Other entities in the filing, including the reporting person in ownership filings, are ignored.
3. If the target CIK is absent, the filing cannot produce a historical sector record.
4. Conflicting SIC codes for the same target CIK within one filing block the record.
5. Conflicting records sharing an accession number block the history build.

## Supported header forms

The parser supports:

- legacy tagged SGML fields such as `<COMPANY-DATA>`, `<CIK>`, and `<ASSIGNED-SIC>`;
- modern complete-submission text fields such as `CENTRAL INDEX KEY` and `STANDARD INDUSTRIAL CLASSIFICATION`.

Only the submission header before the first `<DOCUMENT>` marker is parsed.

## Point-in-time rules

```text
effective_from = available_at
available_at = accepted_at + processing_buffer
```

```text
effective_to = available_at of the next filing that maps to a different sector
```

No sector is emitted before the first valid filing observation. Future filings cannot satisfy an earlier decision. A previously frozen monthly universe is not rewritten unless a new research data version is intentionally created.

## Taxonomy output

The derived `SectorObservation` includes:

- `taxonomy_id`;
- `taxonomy_version`;
- sector code and label;
- effective interval;
- availability timestamp;
- source snapshot and revision.

The raw four-digit SIC observation remains retained for audit and industry-level analysis.

## Fail-closed conditions

- missing/invalid CIK;
- missing accession or acceptance timestamp;
- missing or `0000` SIC;
- conflicting entity SICs;
- mixed instruments or CIKs in one history build;
- overlapping/conflicting accession records;
- decision before the first valid sector observation;
- missing raw snapshot lineage.

## Coverage-crawl amendment — 2026-08-08

For P02-G07, the default filing-header publication buffer is now:

```text
processing_buffer = 3 minutes
```

This supersedes the earlier 1-minute implementation assumption because SEC's current Webmaster FAQ documents a typical 1–3 minute lag from EDGAR system timestamp to public document availability.

The complete-submission parser remains the SIC observation source, but filing existence is established from as-published daily master indexes rather than current submissions history alone. A filing later removed from the current archive remains part of the historical inventory and must be recovered from archival evidence rather than silently ignored.

# P02-PF09 — Alerts + Incident Center

PF09 adds a deterministic, journal-backed operational incident layer to the cumulative Phase 02 repository.

Primary files:

- `src/trading_bot/platform/alerts.py`
- `configs/platform/alert_incident_center.yaml`
- `web/src/pages/IncidentsPage.tsx`
- `tests/unit/platform/test_alerts.py`
- `tests/integration/platform/test_alert_incident_center_flow.py`
- `docs/platform/ALERT_INCIDENT_CENTER_CONTRACT.md`
- `docs/phases/PHASE_02_PF09_ALERT_INCIDENT_CENTER.md`

The web API remains read-only. No paid notification service, broker credential, commercial-data credential or live order path is introduced.

# Read-Only Research Console Contract

**Task:** P02-PF02  
**Phase:** Phase 02B — Pre-Purchase Platform Foundation

## Purpose

Expose Phase 02 research/governance state through a local browser interface without granting trading authority or duplicating strategy logic in the frontend.

## Architecture

```text
PF01 TradeLead / Phase 02 state
              |
              v
 ReadOnlyResearchConsole projections
              |
              v
       FastAPI GET-only API
              |
              v
       React + TypeScript UI
```

The frontend is a presentation layer. It cannot calculate CSMOM-LS scores, universe eligibility, portfolio decisions, broker actions, or point-in-time availability.

## API contract

PF02 exposes only these GET resources:

- `/api/v1/health`
- `/api/v1/overview`
- `/api/v1/leads`
- `/api/v1/watchlist`
- `/api/v1/portfolio`
- `/api/v1/risk`
- `/api/v1/gates`
- `/api/v1/data-health`
- `/api/v1/audit`

No POST, PUT, PATCH, or DELETE operation is permitted. The application validates its generated OpenAPI document when the app is created and fails if a mutation operation is introduced.

## UI views

### Overview

Shows Phase/runtime status, lead counts, synthetic research positions, gate summary, and data health.

### Trade Leads

Displays PF01 deterministic lead artifacts including:

- symbol and decision symbol;
- LONG/SHORT direction;
- frozen score;
- lifecycle state;
- trend state;
- estimated spread/cost;
- authoritative blocking reason;
- strategy version.

Sorting/filtering is presentation-only.

### Watchlist

Shows deterministic blocking reasons and the PF01-derived future qualification action. A Watchlist screen never re-scores a lead.

### Portfolio

PF02 uses synthetic research placeholders only. No broker/account position is represented as real.

### Risk

Displays current Phase 02 hard boundaries. PF04 will later own runtime ACTIVE/REDUCING/HALTED state and protection logic.

### Phase Gates / Data Health

Read-only governance/operational visibility. No UI control can promote a gate.

### Audit Trail

Displays immutable PF01 lead creation records and provenance hashes.

## Security and authority boundaries

PF02 MUST NOT:

- submit, cancel, replace, or modify an order;
- connect to Schwab or another broker;
- store API keys/tokens/passwords in browser storage;
- expose commercial provider credentials;
- contain alpha/strategy formulas in TypeScript;
- promote Phase 03 or procurement authority;
- claim fixture data is live market/account data.

The fixture banner is mandatory while synthetic state is displayed.

## Local development

Backend:

```bash
PYTHONPATH=src uvicorn trading_bot.platform.api.research_api:app --host 127.0.0.1 --port 8000
```

Frontend (on a normal environment with public npm package access):

```bash
cd web
npm install
npm run dev
```

The Vite development proxy sends `/api` requests to `127.0.0.1:8000`.

## Validation

Acceptance requires:

- GET-only OpenAPI surface;
- all expected routes respond against PF01 fixtures;
- mutation methods fail/not exist;
- PF01 lead/watchlist/audit identity consistency;
- React view-model tests;
- TypeScript source validation;
- static scan for secret/browser-storage/broker mutation paths;
- full cumulative Python regression.

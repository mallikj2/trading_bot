# P02-PF02 Research Console

## Run backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-phase02-platform-foundation.txt
PYTHONPATH=src uvicorn trading_bot.platform.api.research_api:app --host 127.0.0.1 --port 8000
```

Open API documentation at `http://127.0.0.1:8000/docs`.

## Run frontend

In a normal developer environment with public npm access:

```bash
cd web
npm install
npm run dev
```

Then open `http://127.0.0.1:5173`.

## Safety

This console is Phase 02 / read-only. It has no broker connectivity and no mutation API routes.

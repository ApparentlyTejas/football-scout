# football-scout

AI-powered football scouting and recruitment platform — a two-person Master's project combining football data, machine learning, tactical analysis, and LLM-based reasoning to identify and explain transfer targets.

See [PROJECT_GUIDE.md](./PROJECT_GUIDE.md) for the full project spec, architecture, and phased implementation plan.

## Repository layout

- `frontend/` — Next.js app
- `backend/` — FastAPI app (API, services, repositories, scout engine, ML, AI)
- `data/` — raw / processed / external datasets (not committed)
- `ml/` — notebooks, experiments, training, evaluation, trained models
- `scripts/` — ingestion, processing, and database scripts
- `docs/` — architecture, API, ML, data, and research documentation
- `docker/` — Docker-related config

## Status

Implementation proceeds incrementally, phase by phase — see section 47 and 60 of `PROJECT_GUIDE.md`.

- [x] Step 1 — Git repository
- [x] Step 2 — Monorepo structure
- [x] Step 6 — FastAPI application (skeleton + health check)
- [ ] Step 3–5 — Docker Compose, PostgreSQL, Redis
- [ ] Step 7 — Next.js application
- [ ] Step 8+ — database models, data ingestion, ML, AI, frontend

### Backend

A minimal FastAPI app lives in `backend/`, with `GET /api/v1/health` as the only endpoint so far. Layering (`api/` → `services/` → `repositories/`) and the `models/`, `schemas/`, `scout/`, `ai/`, `ml/` packages are scaffolded but still empty, awaiting the database phase.

Run it locally:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
# → http://127.0.0.1:8000/api/v1/health
# → http://127.0.0.1:8000/docs
```

Run tests:

```bash
pytest tests/
```

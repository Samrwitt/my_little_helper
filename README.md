# My little helper

Agentic AI scholarship discovery, eligibility matching, deadline tracking, and reminders.

The system is not a static scholarship directory. A user builds a profile once; a **tool-using discovery agent** searches the web, fetches pages through controlled scrapers, extracts structured facts with Gemini (never inventing missing data), deduplicates, scores eligibility, and schedules deadline reminders.

## Quick start

```bash
cp .env.example .env
# Optional: set GEMINI_API_KEY in .env for live AI extraction / query generation

docker compose up --build
```

Host ports (remapped to avoid common local conflicts):

| Service        | URL / port              |
|----------------|-------------------------|
| Frontend       | http://localhost:3001   |
| Backend API    | http://localhost:8001   |
| API docs       | http://localhost:8001/docs |
| PostgreSQL     | localhost:5435          |
| Redis          | localhost:6381          |
| Celery worker  | background              |
| Celery beat    | scheduled jobs          |

> Inside Docker the services still use standard internal ports (`db:5432`, `redis:6379`, `backend:8000`).

### Hybrid local development (DB/Redis in Docker)

If application image builds are slow, you can run API/UI on the host:

```bash
docker compose up -d db redis
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point DATABASE_URL* at localhost:5435 and REDIS at localhost:6381 (see .env)
alembic upgrade head && python -m app.scripts.seed
uvicorn app.main:app --reload --port 8001
celery -A app.tasks.celery_app worker -l info   # separate terminal

cd ../frontend && npm install
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev -- -p 3001
```

**Demo login** (created by seed on first boot):

```text
Email:    demo@scholarship.local
Password: DemoPass123!
```

## Environment variables

See `.env.example`. Important keys:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing |
| `DATABASE_URL` / `DATABASE_URL_SYNC` | Postgres (async + Alembic) |
| `REDIS_URL` / `CELERY_*` | Broker and results |
| `GEMINI_API_KEY` | Gemini API (server-side only) |
| `GEMINI_MODEL` | Default `gemini-2.0-flash` |
| `SMTP_*` | Optional email; without SMTP, emails log to console |
| `DISCOVER_RATE_LIMIT_PER_HOUR` | Manual discovery rate limit |
| `NEXT_PUBLIC_API_URL` | Frontend → API base URL |

Never commit real API keys. The Gemini key is never exposed to the frontend.

## Gemini configuration

1. Create an API key in Google AI Studio.
2. Set `GEMINI_API_KEY` in `.env`.
3. Restart `backend` / `celery_worker`.

Without a key, the app still runs:

- Seed scholarships and heuristic eligibility matching work offline.
- Search-query generation uses deterministic fallbacks.
- Live page extraction is limited until Gemini is configured.

## Database migrations

Migrations run automatically on backend container start (`alembic upgrade head`), then seed runs.

Manual:

```bash
cd backend
alembic upgrade head
python -m app.scripts.seed
```

## Development commands

### Backend (local, without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point DATABASE_URL* and REDIS_URL at local services
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload --port 8000
celery -A app.tasks.celery_app worker -l info
celery -A app.tasks.celery_app beat -l info
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Testing

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

Gemini is mocked / unused in unit tests — no real API calls.

## Architecture

```text
frontend (Next.js)  →  FastAPI  →  PostgreSQL
                           ↓
                     Celery + Redis
                           ↓
        DiscoveryAgent / EligibilityAgent
                           ↓
        SearchProvider | Scraper | GeminiService
```

### Backend layout

```text
backend/app/
  agents/           ScholarshipDiscoveryAgent, EligibilityAgent
  api/              REST routes + JWT deps
  core/             config, security, enums
  db/               SQLAlchemy session + base
  models/           normalized relational models
  schemas/          Pydantic request/response + extraction schemas
  services/
    ai/gemini.py    sole Gemini integration
    search/         provider abstraction + trust scoring
    scraping/       httpx/BS4/Playwright + SSRF guards
    notifications/  in-app + email (+ stubs)
    reminders/      deadline intervals
  tasks/            Celery jobs + beat schedule
  scripts/seed.py   demo data
```

### Agent workflow

`ScholarshipDiscoveryAgent` decides which **explicit tools** to call:

1. `get_user_profile`
2. Generate search queries (Gemini or fallback)
3. `search_web`
4. Prefer official/government/university URLs (trust levels 1.0 / 0.8 / 0.5)
5. `fetch_page` / `render_dynamic_page`
6. `extract_scholarship` (structured JSON; null when unknown)
7. `find_duplicate_scholarship` → merge sources under one canonical record
8. `save_scholarship`
9. `evaluate_eligibility`
10. `schedule_deadline_reminders`

Every run is stored in `agent_runs` + `agent_tool_calls` (inputs/outputs, token usage estimate — **no hidden chain-of-thought**).

### Fact safety

Major facts carry `verified` / `unverified` / `unknown`. Sources are stored in `scholarship_sources`. Aggregators are for discovery; official pages are preferred for deadlines and eligibility.

### Background jobs

| Job | Schedule |
|-----|----------|
| Discover for onboarded users | daily |
| Recheck approaching deadlines | daily |
| General verification refresh | weekly |
| Send deadline reminders | daily |
| Deactivate expired opportunities | daily |

Manual discovery: `POST /agent/discover` (rate-limited).

## API overview

```text
POST /auth/register | /auth/login | /auth/login/json | /auth/refresh
GET  /auth/me
GET|PUT /profile
GET  /dashboard
GET  /scholarships | /scholarships/{id}
POST /scholarships/{id}/save
GET  /matches
GET|POST /applications | PATCH /applications/{id}
PATCH /applications/{id}/documents/{id}
GET  /reminders
GET  /notifications | PATCH /notifications/{id}/read
POST /agent/discover | GET /agent/runs
```

## Security

- Bcrypt password hashing, JWT access + rotating refresh tokens
- CORS allowlist, Pydantic validation, SlowAPI rate limits
- Scraper SSRF protection (localhost, private nets, cloud metadata blocked)
- robots.txt awareness, timeouts, retries, rate limits
- No CAPTCHA/paywall bypass

## License

Portfolio / educational project. Verify all scholarship facts on official sites before applying.

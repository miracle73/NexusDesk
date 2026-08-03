# NexusDesk

Deployable, multi-tenant AI customer support for CiphezNexus. NexusDesk ingests company documents, retrieves tenant-isolated knowledge, and uses a LangGraph workflow to answer, clarify, or escalate each customer message.

## Features

- Company registration and JWT email/password login
- TXT, Markdown and PDF ingestion with overlapping chunks
- Tenant-specific persistent Chroma collections and OpenRouter embeddings
- Grounded RAG answers using `openai/gpt-4o-mini` by default
- LangGraph answer, clarify, and human-escalation decisions
- Stored transcripts, escalation reasons, status management and source names
- Dashboard filters, resolution rate, transcript list and knowledge gaps
- Demo company and FAQ knowledge seeded on first development startup
- Alembic migration, Docker Compose, Render blueprint, backend tests and frontend checks

Every database query and vector collection is scoped by `tenant_id`. Never accept tenant identity from request bodies; it is read from the verified JWT.

## Local setup

1. Copy `.env.example` to `.env`, set `OPENROUTER_API_KEY`, and replace `JWT_SECRET`.
2. Run `docker compose up --build`.
3. Visit [the dashboard](http://localhost:3000) or [API documentation](http://localhost:8000/docs).

Demo login: `demo@cipheznexus.com` / `DemoPass123!`. Change or disable these credentials for a public production environment.

The API runs `alembic upgrade head` before startup. Chroma and PostgreSQL data are stored in Docker volumes.

## API

All authenticated routes use `Authorization: Bearer <token>`.

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`
- `POST /api/v1/documents`, `GET /api/v1/documents`
- `POST /api/v1/chat`
- `GET /api/v1/conversations`, `GET /api/v1/conversations/metrics`
- `GET /api/v1/conversations/{id}`, `PATCH /api/v1/conversations/{id}/status?status=resolved`

## Tests

```bash
cd backend
python -m pip install -e ".[dev]"
pytest
ruff check .

cd ../frontend
npm ci
npm run lint
npm run build
```

## Render deployment

Create a Blueprint from `render.yaml`. In Render, provide `OPENROUTER_API_KEY`, the backend URL in `NEXT_PUBLIC_API_URL` (including `/api/v1`), and the frontend origin in `CORS_ORIGINS`. Render generates the database and JWT secret; the Chroma disk persists tenant vectors.

## Security notes

- `.env`, Chroma data and build outputs are ignored by Git.
- Use a strong generated JWT secret and unique demo password in production.
- Uploads are limited to 10 MB and supported extensions only.
- For larger production deployments, move ingestion to a task queue and use managed object/vector storage.

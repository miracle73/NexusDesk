# NexusDesk

Deployable, multi-tenant AI customer support for CiphezNexus, running as a low-cost serverless MVP. NexusDesk ingests company documents, retrieves tenant-isolated knowledge, and uses a LangGraph workflow to answer, clarify, or escalate each customer message.

## Architecture

| Concern | Service |
| --- | --- |
| API | FastAPI on AWS Lambda behind a Function URL (Mangum adapter) |
| Data | DynamoDB, one on-demand single table |
| Embeddings | Tenant-partitioned vectors stored in the same DynamoDB table |
| Raw uploads | S3 (private, encrypted, 365-day lifecycle) |
| Frontend | Next.js on Cloudflare Pages or Vercel |
| Model | OpenRouter `openrouter/free` |

No API Gateway, Route 53, RDS, EC2, EKS, NAT gateway or load balancer is used. DynamoDB and Lambda stay inside the always-free allowances; only S3 storage may cost a small amount.

### DynamoDB key layout

| Item | pk | sk |
| --- | --- | --- |
| Tenant | `TENANT#<tenant_id>` | `META` |
| User | `USER#<email>` | `META` |
| Document | `TENANT#<tenant_id>` | `DOC#<created_at>#<doc_id>` |
| Conversation | `TENANT#<tenant_id>` | `CONV#<conversation_id>` |
| Message | `CONV#<conversation_id>` | `MSG#<created_at>#<id>` |
| Embedding chunk | `TENANT#<tenant_id>#VEC` | `<doc_id>#<chunk>` |

Every query is rooted at a tenant-prefixed partition key, so no read can cross tenants. Tenant identity is read from the verified JWT only, never from a request body.

## Features

- Immediate company registration and JWT email/password login (no OTP, no email verification)
- TXT, Markdown and PDF ingestion with overlapping chunks, raw file kept in S3
- Tenant-isolated embeddings in DynamoDB with cosine ranking in the Lambda
- Grounded RAG answers via OpenRouter; falls back to the top retrieved chunk when no API key is set
- LangGraph answer, clarify, and human-escalation decisions
- Stored transcripts, escalation reasons, status management and source names
- Dashboard filters, resolution rate, transcript list and knowledge gaps

## Local setup

```bash
cp .env.example .env            # set JWT_SECRET and, optionally, OPENROUTER_API_KEY
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

For a local DynamoDB, run DynamoDB Local and set `DYNAMODB_ENDPOINT_URL=http://localhost:8000`, then create the `pk`/`sk` table once. Leave `UPLOADS_BUCKET` empty to skip S3 writes during development.

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Deploy the backend

```bash
sam deploy --template infra/template.yaml --stack-name nexusdesk --resolve-s3 --capabilities CAPABILITY_IAM --parameter-overrides JwtSecret=<generated-secret> OpenRouterApiKey=<key> CorsOrigins=https://<frontend-domain>
```

The stack creates the DynamoDB table, the uploads bucket and the Lambda Function URL, caps the function with `ReservedConcurrentExecutions` (default 5), and keeps CloudWatch log retention at 7 days. The `FunctionUrl` output is the API base; use `<FunctionUrl>api/v1` as `NEXT_PUBLIC_API_URL`.

## Deploy the frontend

Cloudflare Pages or Vercel, project root `frontend`, build `npm run build`. Set `NEXT_PUBLIC_API_URL` to the Function URL plus `/api/v1`, and add the resulting origin to the stack's `CorsOrigins`.

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
uv sync --extra dev
uv run pytest
uv run ruff check .

cd ../frontend
npm ci
npm run lint
npm run build
```

The backend suite covers signup, login, upload, chat, metrics and cross-tenant isolation against mocked DynamoDB and S3.

## Security notes

- `.env`, local databases, vector data and build outputs are ignored by Git; no keys or secrets are committed.
- Use a strong generated `JWT_SECRET`; pass it as a stack parameter, not in the repository.
- The uploads bucket blocks all public access and is encrypted at rest.
- Lambda concurrency is capped and log retention is short to keep spend predictable.

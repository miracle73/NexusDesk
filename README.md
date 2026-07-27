# NexusDesk

NexusDesk is a multi-tenant AI customer support platform built with FastAPI,
Next.js, LangGraph, OpenRouter, PostgreSQL, and Chroma.

## Repository layout

```text
backend/   FastAPI API and background services
frontend/  Next.js App Router dashboard and chat UI
```

## Quick start

1. Copy `.env.example` to `.env` and add your OpenRouter API key.
2. Start the local services:

   ```bash
   docker compose up --build
   ```

3. Open:
   - Frontend: http://localhost:3000
   - Backend API docs: http://localhost:8000/docs

This is the initial project scaffold. Authentication, document ingestion, RAG,
LangGraph orchestration, conversations, analytics, and seed data will be added
on top of this foundation.

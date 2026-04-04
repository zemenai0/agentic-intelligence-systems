# Agentic Intelligence Systems

Private HabitaLife agent service for backend-to-agent orchestration.

## What Is Implemented

This repository now contains a working FastAPI service for the agent side of
HabitaLife. The current implementation includes:

- private agent endpoints for `respond`, `recommend`, `sentiment/score`, and
  `memory/summarize`
- strict Pydantic contracts aligned to the design docs
- modular orchestration and specialized agent modules
- backend route mapping and client abstractions
- unit tests for the first MVP flows

The service does not own canonical business state. It assumes the backend owns
bookings, rooms, service requests, proposal persistence, and final write
execution.

## Python Baseline

This project targets Python 3.12.3.

## Quick Start

```bash
uv sync --extra test
cp .env.example .env
uv run uvicorn agentic_intelligence_systems.api:app --reload
```

## Terminal Chat

You can also talk to the agent directly from the terminal without `curl`:

```bash
uv run habitalife-chat
```

Useful commands inside the chat:

- `/show`
- `/resort <id>`
- `/booking <id>`
- `/room <id>`
- `/tools all`
- `/quit`

## Admin CLI

You can seed realistic demo room inventory from the terminal:

```bash
uv run habitalife-admin seed-demo-rooms \
  --resort-id 80c8fec6-8cda-47a5-9dc2-e7ac6ab53f75
```

Preview the payloads first:

```bash
uv run habitalife-admin seed-demo-rooms \
  --resort-id 80c8fec6-8cda-47a5-9dc2-e7ac6ab53f75 \
  --dry-run
```

## Provider Configuration

The service can run with the deterministic fallback provider or with Gemini.

- `GEMINI_API_KEY`: required when `LLM_PROVIDER=gemini`
- `LLM_PROVIDER`: defaults to `gemini` when `GEMINI_API_KEY` is present,
  otherwise `deterministic`
- `GEMINI_MODEL`: defaults to `gemini-flash-latest`
- `GEMINI_BASE_URL`: defaults to `https://generativelanguage.googleapis.com`
- `BACKEND_BASE_URL`: backend API base URL from the Postman collection.
  This is required in deployed environments and must not point at
  `localhost`.
- `BACKEND_AUTH_MODE`: `none`, `api_key`, or `bearer`
- `BACKEND_SERVICE_TOKEN`: backend bearer token when service-to-service auth is enabled

## Main Endpoints

- `GET /health`
- `POST /internal/agent/respond`
- `POST /internal/agent/recommend`
- `POST /internal/agent/sentiment/score`
- `POST /internal/agent/memory/summarize`

## Package Naming

The repository name uses hyphens, but the Python package uses underscores:

```python
import agentic_intelligence_systems
```

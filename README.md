# AI Social Media Intelligence — Stage 1: Backend + Mock API

## Run
    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000
Docs (Swagger): http://localhost:8000/docs — works with no API keys (mock data, seeded and reproducible).

## Endpoints
/api/dashboard, /posts, /sentiment, /emotions, /demographics, /trends, /topics, /timeline (?at=ISO_HOUR for click-through),
/network, /influencers, /diffusion/{topic_id}, /platforms, /search?q=. Filters: `platform`, `days`.

## PostgreSQL (optional at this stage)
    createdb social_intel && psql social_intel -f database/schema.sql
The mock service serves from memory; wiring it to Postgres is the next stage.

## Real APIs later
Implement `XDataService` / `TelegramDataService` with the same `posts()` interface as `MockDataService` in `main.py`,
read `X_API_KEY` / `TELEGRAM_BOT_TOKEN` from the environment (see `.env.example`), and switch via `DATA_MODE`.

## Privacy
Anonymized IDs only; demographics are aggregate and labelled "Estimated / Aggregate".

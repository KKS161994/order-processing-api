# order-processing-api
Production-grade order processing API with auth, rate limiting, caching, and observability — FastAPI + Postgres + Redis

# order-processing-api

Production-grade order processing API demonstrating senior-level patterns: authentication, rate limiting, caching, idempotency, concurrency safety, and observability. Built with FastAPI, Postgres, and Redis.

## Problem statement

A REST API for an order processing system, covering the full lifecycle from user creation through order placement, payment, and webhook handling. Designed to demonstrate production patterns that separate senior-level work from tutorial-level work.

## What the design demonstrates

Will be filled in as the project develops. Planned coverage: layered architecture (controller/service/repository), JWT authentication with role-based access control, Redis-backed rate limiting (token bucket and sliding window), cache-aside with stampede protection, optimistic locking for concurrency safety, idempotency keys for retry-safe payments, structured logging with request IDs, and Prometheus metrics.

## Tech choices

- **Framework:** FastAPI — async by default, automatic OpenAPI docs, type-checked via Pydantic
- **Database:** Postgres with SQLAlchemy ORM, Alembic for migrations
- **Cache:** Redis (added in Week 2)
- **Auth:** JWT (added in Week 2)
- **Testing:** pytest + httpx
- **Language:** Python 3.12+

## How to run locally

### Prerequisites
- Python 3.12+
- (Coming Week 2) Postgres, Redis

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run
```bash
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

### Test
```bash
pytest tests/
```

### Smoke check
```bash
curl http://localhost:8000/health
curl http://localhost:8000/version
```

## What was non-obvious during the build

Engineering journal entries — filled in as decisions are made and bugs are debugged.



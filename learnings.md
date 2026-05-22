# Learnings — order-processing-api

## 2026-05-22 (Day 1)

Project scaffolding for the 6-week Rippling endpoint prep arc.

- **Layered structure from day one:** `app/api/`, `app/service/`, `app/repository/`, `app/models/`, `app/config/`. Even though today's code is one main.py file, the directories communicate architectural intent. Future commits fill the layers; the boundaries are visible from commit 1.
- **`/health` is liveness-only.** No dependency checks. Carrying forward the lesson from k8s-multi-service-deploy — checking dependencies inside liveness causes unnecessary pod restarts during transient downstream issues. A separate `/ready` will come later when there are actual dependencies to gate on.
- **`/version` is operational hygiene.** During incidents, on-call always asks "what version is running?" Adding it now means it's not a scramble later.
- **Pydantic settings for config.** Environment-driven configuration with typing and validation at load time. Beats `os.environ.get()` scattered through code.

Next session (Saturday marathon): Postgres setup, SQLAlchemy models, Alembic migration for users/orders/payments/idempotency_keys, first CRUD endpoints.

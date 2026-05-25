# Learnings — order-processing-api

## 2026-05-22 (Day 1)

Project scaffolding for the 6-week Rippling endpoint prep arc.

- **Layered structure from day one:** `app/api/`, `app/service/`, `app/repository/`, `app/models/`, `app/config/`. Even though today's code is one main.py file, the directories communicate architectural intent. Future commits fill the layers; the boundaries are visible from commit 1.
- **`/health` is liveness-only.** No dependency checks. Carrying forward the lesson from k8s-multi-service-deploy — checking dependencies inside liveness causes unnecessary pod restarts during transient downstream issues. A separate `/ready` will come later when there are actual dependencies to gate on.
- **`/version` is operational hygiene.** During incidents, on-call always asks "what version is running?" Adding it now means it's not a scramble later.
- **Pydantic settings for config.** Environment-driven configuration with typing and validation at load time. Beats `os.environ.get()` scattered through code.

Next session (Saturday marathon): Postgres setup, SQLAlchemy models, Alembic migration for users/orders/payments/idempotency_keys, first CRUD endpoints.

## 2026-05-24 (Day 2)

- What is the contract? POST /orders, requires user_id and positive amount, returns Order with 201, returns 404 if user missing, 422 if validation fails
- What can fail? DB connection failure (500). User check passes but order create fails mid-transaction (500, but DB transaction rolls back). Network timeout from client (retry with idempotency key — coming Day 12).
- What happens under retry? Currently not idempotent. A retry creates a duplicate order. This is a Day 12 fix.
- What happens under concurrency? Two requests creating orders for the same user are safe (no shared state). Two requests creating orders that share an inventory item would conflict — not modeled here, but would need either a unique constraint at DB level or app-level locking.
- What should be strongly consistent? Order creation must be transactional with any future inventory deduction. Eventual consistency is fine for downstream notifications/analytics.
- How do we observe it? Currently no observability. Day 13 adds request IDs, structured logs, Prometheus metrics for request count, latency, error rate.
- How do we roll it back? DB migrations are reversible via Alembic downgrade. Application rollback via image tag rollback (covered in K8s project).
- How do we make junior engineers maintain it? Layered architecture (controller/service/repository) means each piece is independently testable and replaceable. Domain exceptions translate cleanly to HTTP. Pydantic at the boundary catches misuse early.

LLD decision today: Separated services from repositories. Could have kept business logic 
inline in controllers (simpler today). Chose service layer because:
1. Business rules ("user must exist for order creation") belong in one place, not duplicated 
   across endpoints
2. Domain exceptions (UserNotFound) are HTTP-framework-agnostic — could be called from a 
   worker, gRPC handler, or CLI without rewriting
3. Tests can verify business logic without spinning up FastAPI test client
Tradeoff accepted: more files, more layers. Worth it for any project beyond a 
single-endpoint demo.

## End-of-marathon reflection

The cognitive shift today was hands working faster than conscious deliberation. By Hour 3, the layering (controller → service → repository → ORM) felt automatic. By Hour 4, refactoring controllers to use services took 10 minutes for something that would have taken an hour at the start.

What automaticity covers now:
- Engine + SessionMaker + Session lifecycle
- ORM models with intentional column choices (Decimal for money, indexed FKs, UTC timestamps)
- Pydantic schemas as API boundary, separate from ORM
- Repository → Service → Controller layering
- Domain exceptions translated to HTTP at controller boundary
- Alembic autogenerate + apply

This is the muscle that interview pressure tests. It's not knowledge; it's reflex. Building it requires reps, not reading. Today was one rep.
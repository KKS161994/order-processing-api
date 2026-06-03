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


## 2026-05-25 (Day 4)

Active recall review of Saturday's marathon material. Gaps found:
- [list what you got wrong or fuzzy on in Phase 1 — be honest, this is the most valuable part of today]

Then: consistent error envelope work.

**Error contract design:**
- One shape for every error: error.code (human-readable string like "not_found"), error.message, error.status, error.timestamp. Optional details (for validation errors with field-level info) and request_id (Week 3 hook).
- Consumers parse all errors the same way regardless of which endpoint produced them. SDE 2 APIs often have ad-hoc error shapes per endpoint — frontends end up writing custom error parsers for each case.
- The timestamp on every error is small but real — when a user says "the API errored at 3:47pm" you can find logs by time.

**Input normalization:**
- Email lowercased + stripped. Without this, "Alice@example.com" and "alice@example.com" become two different users in practice — duplicate accounts.
- Name stripped + empty-after-strip rejected. Frontend forms send messy input; backend is the source of truth for normalization.
- `field_validator` is Pydantic v2; `validator` is v1. Today's project is v2.

**Applied LLD decision today:**
Defined exception handlers at the FastAPI level rather than catching and re-formatting in each endpoint. Alternative was per-endpoint try/except returning JSONResponse manually. Centralized wins because (a) no risk of forgetting it in a new endpoint (b) one place to evolve the error contract (c) controller code stays focused on happy path.

Next session: refine read endpoints with pagination edge cases.


## 2026-06-02 (Day 5 — back after 9-day illness)

**Revision phase recall results:**
- [List what you got right and what you fumbled on the 4 questions]
- Gaps to re-touch: [whatever wasn't reflexive]

**Build: pagination wrappers + cursor variant.**

Generic Pydantic models with TypeVar give one wrapper per pagination style,
reusable across all list endpoints. Two wrappers because the metadata shapes
are genuinely different — sharing would force optional fields everywhere.

Repository: list_by_user_after uses keyset pagination — `where id < cursor`.
O(limit) regardless of position. Stable across inserts because the cursor is
a real row id, not a positional offset.

Service: offset variant returns (items, total) tuple. Cursor variant returns
just list — controller computes next_cursor from the last item. Both
framework-agnostic — could serve gRPC, CLI, anything.

**Offset vs cursor pagination — the tradeoff:**

Offset:
- Pro: simple, supports jumping to arbitrary pages, native total count
- Con: O(offset) DB scan — page 1000 is slow. Inconsistent results if rows
  are inserted/deleted between requests (skips or duplicates)
- Use for: admin dashboards, search results with page numbers

Cursor (keyset):
- Pro: O(limit) regardless of position. Stable across concurrent inserts.
- Con: can't jump to arbitrary pages. No native total count.
- Use for: user-facing feeds, infinite scroll, "load more" UIs

This is staff-level signal because most candidates know one pattern; few
have implemented both on the same project and can verbalize when each fits.

**Applied LLD decision today:**
Two distinct PaginatedResponse types instead of one with optional fields.
Tradeoff: more code, slightly more wrapper definitions. Won the call because:
- Each response model is exhaustively typed — no runtime "is offset None or
  is cursor None" branching
- Documents intent at the type level — the API contract is self-evident
- Adds a third variant later (e.g., time-based) without polluting existing types

**Energy check:**
Re-entry felt OK. Revision phase was worth the 15 min — without it I'd have
spent 20+ min looking up patterns mid-flow. Mild weakness still there at the
end of the 90 min, but no GI flare. Tomorrow normal cadence assumed.

Next: Day 6 (Wed Jun 3) — testing. pytest expansion to ≥10 tests covering
CRUD, validation, error envelope, and both pagination variants.


## 2026-06-03 (Day 6 — testing)

**Revision phase recall:**
- [List the 4 questions and what you got right/fumbled]
- Gaps to re-touch: [whatever wasn't reflexive]

**Build: pytest suite, 13 tests covering CRUD + pagination.**

Test infrastructure design:
- Separate test database (`order_processing_test`) so tests never touch dev data
- drop_all + create_all per test = simple, reliable, slow. Acceptable at 13 tests.
  When suite grows to 50+, switch to transaction-rollback isolation (start txn at
  fixture entry, rollback at fixture exit — each test runs in a discarded txn)
- `app.dependency_overrides[get_db] = override_get_db` is FastAPI's mechanism for
  swapping dependencies in tests. Same pattern used later for Redis, payment
  gateway, etc.
- `scope="function"` on fixtures = fresh state per test. Slow but isolated.
  `scope="session"` = setup shared across all tests (use for expensive
  immutable resources only)

**Test design principles applied:**
- One test per concern. `test_create_user_normalizes_email_and_name` tells you
  what failed when it breaks. SDE 2 anti-pattern: `test_create_user_1`, `test_2`,
  etc. — destroys the value of the suite.
- Assert the error envelope shape, not just the status code. Catches a
  regression where someone removes the custom handlers (would still return
  HTTP 409 but with FastAPI's default shape, not yours).
- Setup inline where it's small. One `_create_user` helper, no fixture yet.
  Extract to a fixture only when ≥3 tests need the same setup.

**Applied LLD decision today:**
Test database is a separate Postgres database, not SQLite in-memory.
Tradeoff: slower tests, requires Postgres running. Won the call because
SQLAlchemy 2.0 dialect features (server_default=func.now, Numeric precision,
timezone-aware DateTime) behave differently in SQLite vs Postgres — tests
that pass on SQLite can fail in production. Better to test against the real
DB engine even at the cost of speed.

**Energy check:** Held up through the 90 min, no GI flare, mild fatigue at
the end (expected). Tomorrow continues normal cadence.

Next: Day 7 (Thu Jun 4) — start Week 2 with JWT auth. Login endpoint,
token generation, validation middleware.
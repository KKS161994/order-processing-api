# Cheatsheet — order-processing-api

A working reference for patterns, commands, and decisions used in this project. Updated as the project evolves.

---

## Quick index — common tasks

- **Start the day**: `open -a Docker` → `docker compose up -d postgres` → `source .venv/bin/activate`
- **Run the API**: `uvicorn app.main:app --reload --port 8000`
- **Run tests**: `pytest tests/`
- **Generate a migration**: `alembic revision --autogenerate -m "<description>"`
- **Apply migrations**: `alembic upgrade head`
- **Rollback one migration**: `alembic downgrade -1`
- **Check DB tables**: `docker compose exec postgres psql -U orderapi -d order_processing -c "\dt"`
- **Connect to DB shell**: `docker compose exec postgres psql -U orderapi -d order_processing`
- **End the day**: commit + push → `docker compose down` (preserves data via named volume)

---

## Project structure

```
order-processing-api/
├── app/
│   ├── api/              # Controllers — HTTP translation only
│   │   ├── schemas.py    # Pydantic request/response DTOs
│   │   ├── users.py      # User route handlers
│   │   └── orders.py     # Order route handlers
│   ├── service/          # Business logic + domain exceptions
│   │   ├── user_service.py
│   │   └── order_service.py
│   ├── repository/       # Data access layer
│   │   ├── user_repository.py
│   │   └── order_repository.py
│   ├── models/           # ORM models (DB shape)
│   │   ├── user.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── idempotency.py
│   ├── db/
│   │   └── session.py    # Engine, SessionLocal, get_db dependency, Base
│   ├── config/
│   │   └── settings.py   # Pydantic-settings env config
│   └── main.py           # FastAPI app + router includes
├── alembic/              # Migration scripts
│   ├── env.py            # Alembic environment config
│   └── versions/         # Generated migration files
├── tests/
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
└── README.md
```

**Layering rule:** API → Service → Repository → ORM. Imports flow downward, never upward. Repository doesn't know API exists. Service doesn't know HTTP exists.

---

## SQLAlchemy — engine, sessionmaker, session

- **Engine** = pool of connections. App-wide singleton.
- **SessionMaker** = factory for sessions. Knows the engine + defaults.
- **Session (`db`)** = short-lived unit of work. Holds one connection, one transaction, an identity map.

```python
# One per app, lives forever — connection pool + dialect
engine = create_engine(db_url, pool_pre_ping=True, echo=...)

# Factory that produces Sessions preconfigured with engine + transaction settings
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### FastAPI dependency for DB session

```python
from collections.abc import Iterator

def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        try:
            yield db
            db.commit()        # commit at request boundary
        except Exception:
            db.rollback()
            raise
```

- Use `Iterator[Session]` (not `Session`) — it's a generator.
- `with` handles `close()` automatically. No try/finally needed for cleanup.
- Commit at the boundary so the whole request is atomic.

---

## SQLAlchemy 2.0 query style

| 1.x (legacy) | 2.0 (modern) |
|---|---|
| `db.query(User)` | `select(User)` |
| `.filter(...)` | `.where(...)` |
| `.first() / .all()` | terminator on Result (see below) |

```python
from sqlalchemy import select

# Single row — assert at most one
db.execute(select(User).where(User.email == e)).scalar_one_or_none()

# Many rows
db.execute(select(Order).where(Order.user_id == uid)).scalars().all()

# Shortcuts
db.scalar(select(User).where(...))         # one
db.scalars(select(Order).where(...)).all() # many

# PK lookup (uses identity map cache)
db.get(User, user_id)
```

### Result terminators

| One row | Many rows |
|---|---|
| `.scalar()` | `.scalars().all()` |
| `.scalar_one()` | `.scalars().one()` |
| `.scalar_one_or_none()` | `.scalars().one_or_none()` |
|  | `.scalars().first()` |

**scalar (singular) ≠ scalars (plural).** Plural gives an iterable; singular gives one value.

---

## ORM model — Mapped + mapped_column

```python
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### Column-by-column reference

| Pattern | Why |
|---|---|
| `Mapped[type]` + `mapped_column(...)` | SQLAlchemy 2.0 style. Type-annotated, IDE-friendly |
| `Mapped[int \| None]` + `nullable=True` | Optional column |
| `primary_key=True` | PK |
| `index=True` | B-tree index. Use on FKs and frequently filtered/sorted columns |
| `unique=True, index=True` | Unique constraint plus index (typical for email) |
| `ForeignKey("users.id")` | FK constraint at DB level |
| `Numeric(10, 2)` for money | NEVER use `Float` for currency — floating-point math is wrong for money |
| `String(255)` (with length) | Always cap string length where it makes sense |
| `String(3)` for currency codes | ISO 4217 codes are 3 chars (USD, EUR, GBP) |
| `DateTime(timezone=True)` | Always timezone-aware. Naive timestamps cause production bugs |
| `server_default=func.now()` | DB sets the default at INSERT time — consistent regardless of app server |
| `onupdate=func.now()` | Auto-update on every modification (for `updated_at` columns) |
| `default=1` (Python-side) | Default applied by SQLAlchemy when creating the object, before INSERT |

### func — SQL function namespace

```python
from sqlalchemy import func

func.now()           # NOW()
func.count()         # COUNT(*)
func.lower(col)      # LOWER(col)
func.coalesce(a, b)  # COALESCE(a, b)
```

Anything you call on `func` becomes a SQL function. Use it for server defaults and queries — never replace with raw strings.

### Indexing

```python
email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
```

- `index=True` → B-tree index. NULLs are indexed.
- `unique=True` → unique index (counts as an index too).

For nullable columns dominated by NULLs, prefer a partial index:

```python
__table_args__ = (
    Index("ix_x_y", "y", postgresql_where="y IS NOT NULL"),
)
```

---

## Repository vs Service

- **Repository** = collection API for one model. CRUD. Talks to one data source.
- **Service** = orchestrator. Combines multiple repos + external systems (Stripe, email, etc.).

```python
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()      # NO commit here — owner is the caller
        return user
```

**Rule:** repositories `add` + `flush`. They never commit. Commit happens once, in `get_db`.

### Transactions

- One request = one transaction (commit/rollback in `get_db`).
- `flush()` sends SQL inside the current txn; populates IDs and server defaults.
- `commit()` ends the txn.
- `refresh(obj)` re-reads a row from DB — rarely needed after `flush()`.
- For sub-transactions inside a service: `with db.begin_nested(): ...` (SAVEPOINT).

---

## Pydantic schemas (DTOs)

Separate from ORM models. **Never expose ORM models through the API.**

```python
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):                # incoming JSON
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)


class UserResponse(BaseModel):              # outgoing — ORM-backed
    id: int
    email: str
    name: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)   # Pydantic v2 idiom
    # (v1 idiom: class Config: from_attributes = True)


class OrderCreate(BaseModel):
    user_id: int
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
```

### Validators

| Validator | What it does |
|---|---|
| `EmailStr` | Validates email format. Requires `pip install email-validator` |
| `Field(min_length=1, max_length=255)` | String length bounds |
| `Field(gt=0)` | Numeric: must be greater than zero |
| `Field(ge=0)` | Numeric: ≥ 0 |
| `Field(default=..., ...)` | Default value with validation |
| `Field(decimal_places=2)` | Decimal: max 2 decimal places |
| `from_attributes=True` | Build response from ORM object attributes (not dict) |

---

## Domain exceptions vs HTTP exceptions

```python
# In service layer — domain exception, framework-agnostic
class UserNotFound(Exception):
    pass


class UserService:
    def get_user(self, user_id: int) -> User:
        user = self.repo.get_by_id(user_id)
        if user is None:
            raise UserNotFound(f"user {user_id} not found")
        return user


# In controller — translate to HTTP
@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    service = UserService(db)
    try:
        return service.get_user(user_id)
    except UserNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
```

**Why:** the service is reusable from CLI, gRPC, workers, or tests without the FastAPI dependency.

### The shape of one full endpoint

```python
@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
):
    service = OrderService(db)
    try:
        order = service.create(user_id=payload.user_id, amount=payload.amount)
    except UserNotFound:
        raise HTTPException(status_code=404, detail="user not found")
    return order
```

**Boundary translation rules:**
- Pydantic at the edges (request + response schemas).
- Domain exceptions in services (`UserNotFound`, not `HTTPException`).
- `HTTPException` only in the router — services stay framework-agnostic.

---

## HTTP status codes that matter

| Code | When |
|---|---|
| 200 OK | Default success, GET responses |
| 201 Created | Successful POST that created a resource |
| 204 No Content | Successful operation with no response body (e.g., DELETE) |
| 400 Bad Request | Generic client error |
| 401 Unauthorized | Missing or invalid auth credentials |
| 403 Forbidden | Authenticated but not permitted |
| 404 Not Found | Resource doesn't exist |
| 409 Conflict | Operation conflicts with current state (duplicate, version mismatch) |
| 422 Unprocessable Entity | FastAPI default for Pydantic validation failures |
| 429 Too Many Requests | Rate limited (coming Week 2) |
| 500 Internal Server Error | Server-side bug, unhandled exception |
| 503 Service Unavailable | Downstream dependency unavailable (cache, DB) |

---

## Decorators

`@something` above a function rewrites:

```python
@router.get("/path")
def f(): ...
```

…as:

```python
def f(): ...
f = router.get("/path")(f)
```

That's it — `@` is just function composition with prettier syntax. `router.get(...)` returns a decorator that registers `f` as a route and returns `f` unchanged.

---

## Alembic — migrations

### Initial setup (one-time)

```bash
alembic init alembic
```

Then edit `alembic/env.py` to wire in app settings and models:

```python
from app.config.settings import settings
from app.db.session import Base
from app.models.user import User                # noqa: F401
from app.models.order import Order              # noqa: F401
from app.models.payment import Payment          # noqa: F401
from app.models.idempotency import IdempotencyKey  # noqa: F401

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
# delete the scaffold's "target_metadata = None" line — it overwrites the above
```

`noqa: F401` silences the unused-import lint — these imports run for their side effect (registering each model on `Base.metadata`).

The key is `sqlalchemy.url` (dot), not `sqlalchemy_url` (underscore).

### Daily commands

| Command | What it does |
|---|---|
| `alembic revision --autogenerate -m "description"` | Generate migration from model diffs |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic upgrade +1` | Apply one migration |
| `alembic downgrade -1` | Rollback one migration |
| `alembic downgrade base` | Rollback to nothing |
| `alembic current` | Show current revision |
| `alembic history` | Show migration history |
| `alembic show <revision>` | Show a specific migration |

### Migration workflow

1. Edit/add a model in `app/models/`
2. Import it in `alembic/env.py` (if new model)
3. `alembic revision --autogenerate -m "create xyz table"` — generates a file in `alembic/versions/`
4. **Read the generated file before applying.** Autogenerate is good but not perfect.
5. `alembic upgrade head` to apply
6. Commit BOTH the model change AND the generated migration file together

**Senior discipline:** never edit a migration after it's been applied outside your local dev. Create a new migration that fixes it instead. Editing applied migrations breaks team sync.

### Golden rule

Never delete a migration file after it's been applied. Always `alembic downgrade -1` first, then delete. Otherwise you orphan `alembic_version`.

### Recovery from orphaned alembic_version

```bash
# Dev only — wipes the DB
docker compose down -v && docker compose up -d
alembic upgrade head
```

---

## Docker — Postgres lifecycle

| Command | What it does |
|---|---|
| `docker compose up -d postgres` | Start Postgres in background (`-d` = detached) |
| `docker compose ps` | List running compose services |
| `docker compose down` | Stop and remove containers (named volume preserves data) |
| `docker compose down -v` | Stop AND remove volumes (DELETES data — only when starting fresh) |
| `docker compose logs postgres` | View Postgres logs |
| `docker compose logs -f postgres` | Follow logs in real time |
| `docker compose exec postgres pg_isready -U orderapi -d order_processing` | Healthcheck |
| `docker compose exec postgres psql -U orderapi -d order_processing` | Open psql shell inside container |
| `docker compose restart postgres` | Restart just Postgres without losing other compose state |

---

## psql — DB inspection

Inside psql shell (`docker compose exec postgres psql -U orderapi -d order_processing`):

| Command | What it does |
|---|---|
| `\dt` | List all tables |
| `\d <table>` | Describe a table (columns, types, indexes, constraints) |
| `\d+ <table>` | Same, with extended info (storage, comments) |
| `\di` | List indexes |
| `\du` | List users/roles |
| `\l` | List databases |
| `\c <dbname>` | Switch database |
| `\timing` | Toggle query timing |
| `\x` | Toggle expanded display (rows shown vertically) |
| `\q` | Quit |
| `EXPLAIN ANALYZE <query>;` | Query plan + actual execution stats. The performance-debugging command |

---

## pytest — testing

### Basic test

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

### Commands

| Command | What it does |
|---|---|
| `pytest tests/` | Run all tests |
| `pytest tests/test_health.py` | Run one file |
| `pytest tests/test_health.py::test_name` | Run one test |
| `pytest -v` | Verbose output |
| `pytest -s` | Show print statements |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Re-run only last-failed tests |
| `pytest -k "health"` | Run tests matching name pattern |

---

## Settings — Pydantic-settings pattern

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "order-processing-api"
    environment: str = "development"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "order_processing"
    db_user: str = "orderapi"
    db_password: str = "orderapi_dev_password"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
```

| Pattern | Why |
|---|---|
| `BaseSettings` | Auto-loads from environment variables |
| Type annotations | Validation at load time, not at use time |
| Default values | Override-friendly: only set env vars you want different |
| `database_url` as `@property` | Computed from parts. Don't store both parts AND assembled string — single source of truth |
| `env_file = ".env"` | Local dev overrides via .env (don't commit .env) |

---

## Imports — common spots

```python
from collections.abc import Iterator, Generator, Sequence   # modern, not from typing
from sqlalchemy import select, ForeignKey, String, Numeric, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, Session, sessionmaker, DeclarativeBase
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status
```

---

## Common bugs — the missing-() family

```python
db.close            # WRONG — method reference, not a call
db.close()          # right

.scalars.all()      # WRONG
.scalars().all()    # right

mapped_column[String(255), unique=True]   # WRONG — subscript, can't take kwargs
mapped_column(String(255), unique=True)   # right

email.lower         # WRONG — method object
email.lower()       # right
```

### Cousin bug: shadowed builtins

```python
self.repo.get_by_id(id=id)         # WRONG — `id` here is the built-in function
self.repo.get_by_id(id=user_id)    # right
```

Don't name parameters `id, type, list, str, dict, input, filter, map`. They collide with built-ins.

### Driver error decoder

```
cannot adapt type 'builtin_function_or_method' using placeholder '%s'
```

= "you passed a Python function as a SQL parameter." Look for either a missing `()` or a built-in shadowed by accident.

---

## Debugging multi-Postgres confusion

`localhost:5432` may have two servers (Docker + native). Tools that help:

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN                            # who's listening
docker compose exec postgres psql -U <u> -d <db> -c '\dt'   # talk to container
psql -h localhost -p 5432 -U <u> -d <db>                    # whatever's on loopback
```

**Diagnosis pattern:** when "X doesn't exist" but you just verified X exists, you're talking to the wrong instance.

---

## Python packages

- **Module** = one `.py` file.
- **Package** = a directory of modules. `__init__.py` is technically optional (Python 3.3+ namespace packages), but include it — predictable, signals intent, place for re-exports.

---

## Layered architecture — what lives where

| Layer | Knows about | Doesn't know about |
|---|---|---|
| **Controller** (`app/api/*.py`) | HTTP, status codes, Pydantic schemas, FastAPI | Business rules, DB schema |
| **Service** (`app/service/*.py`) | Business rules, domain exceptions | HTTP, SQL, ORM mechanics |
| **Repository** (`app/repository/*.py`) | DB queries, ORM models | Business rules, HTTP |
| **Model** (`app/models/*.py`) | DB schema (table, columns, FKs) | Anything app-side |
| **Schema** (`app/api/schemas.py`) | API contract (request/response shape) | DB schema, business rules |

---

## Concepts worth re-reading

### Saturday May 23 — Marathon 1

1. **Layered architecture is the spine of senior backend code.** API → Service → Repository → ORM. Each layer has one job. Imports flow downward only. This is what makes the codebase testable, swappable, and maintainable by junior engineers.

2. **ORM models and API schemas are deliberately separate.** ORM = DB shape. Pydantic schema = API contract. Conflating them couples DB changes to API consumers. Senior default: keep them separate from day one, even if they look similar.

3. **Domain exceptions are framework-agnostic.** `UserNotFound` lives in the service layer. The controller translates it to HTTP 404. The service could be called from a gRPC handler, CLI, or background worker without modification.

4. **Money is `Decimal(10, 2)`, never `Float`.** Floating-point math is wrong for currency. `0.1 + 0.2` in IEEE 754 is not 0.3. Non-negotiable senior discipline.

5. **Timestamps are timezone-aware (`DateTime(timezone=True)`) and UTC.** Naive timestamps cause production bugs that surface during DST transitions. `server_default=func.now()` ensures the DB sets it, not the app.

6. **Indexes on FKs and frequently-filtered columns are non-negotiable.** Without `index=True` on `Order.user_id`, listing a user's orders becomes a sequential scan at scale.

7. **Repository pattern means the service doesn't know SQLAlchemy exists.** Tests mock the repository, not the DB. DB engine swap is a one-file change.

8. **Pydantic validates at the API boundary.** Don't validate in the service layer (duplication) or the repository (too late). Catch invalid input the moment it crosses into your system.

9. **HTTP status codes have semantics.** 201 for create. 404 for missing. 409 for conflict. 422 for validation. Senior engineers care about these; SDE 2 candidates often default to 200/500.

10. **Alembic autogenerate is good but not perfect — read every generated migration before applying.** Especially for renames, index changes, or anything involving constraints.

11. **`pool_pre_ping=True` is the senior default for connection pools.** Detects stale connections before use. Prevents the production bug where Postgres restarts overnight and your app pool still has dead connections at 9am.

12. **Cognitive automaticity is the muscle that interview pressure tests.** Hands moving faster than conscious thought. Built by reps, not reading. Marathon 1 was one rep.

### Applied LLD decision — Saturday May 23

**Decision:** Service layer between controllers and repositories.

**Alternative considered:** Keep business logic inline in controllers (simpler today).

**Why the service layer wins:**
- Business rules ("user must exist for order creation") live in one place, not duplicated across endpoints
- Domain exceptions are HTTP-framework-agnostic — callable from gRPC, CLI, or workers without rewriting
- Tests verify business logic without spinning up FastAPI test client
- The boundary between "is this allowed" and "how do I return it" becomes explicit

**Tradeoff accepted:** more files, more layers. Worth it for any project beyond a single-endpoint demo.

---

## Anti-patterns to avoid

- **`from app.models import *` in `__init__.py`** — Alembic gets confused, circular imports happen. Import models explicitly.
- **Returning ORM models from endpoints without `response_model`** — leaks internal fields, breaks API contract on model changes.
- **Validating in the service layer** — duplicates Pydantic. Validate at the boundary, trust the data after.
- **`Float` for money** — wrong. Period.
- **Naive `datetime.now()`** — timezone bugs in production. Use `datetime.now(timezone.utc)` or let Postgres handle it via `server_default=func.now()`.
- **No index on FKs** — sequential scans at scale.
- **Editing applied migrations** — breaks team sync. Create a new migration that fixes the issue instead.
- **`echo=True` in production** — logs every SQL query. Performance hit AND leaks data into logs.
- **Storing both parts AND assembled string in settings** — drift. Compute the URL via `@property`.
- **Empty `except:` clauses** — swallows everything including KeyboardInterrupt. Always catch specific exceptions.
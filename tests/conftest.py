"""Shared pytest fixtures.

Strategy
--------
Each test runs against a dedicated ``order_processing_test`` database. The DB
is created once per pytest session and its schema is built from SQLAlchemy
metadata. Between tests every table is truncated, so no test can see another
test's data.

The application's ``get_db`` dependency is overridden so route handlers
receive a session bound to the test engine, not the dev DB.
"""

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.db.session import Base, get_db
from app.main import app

TEST_DB_NAME = f"{settings.db_name}_test"
TEST_DATABASE_URL = (
    f"postgresql+psycopg://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{TEST_DB_NAME}"
)


def _ensure_test_database() -> None:
    admin_url = (
        f"postgresql+psycopg://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/postgres"
    )
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).first()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_test_database()
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        with engine.begin() as conn:
            tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
            conn.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client):
    def _make(*, email: str | None = None, name: str = "Test User") -> dict:
        email = email or f"user-{uuid.uuid4()}@example.com"
        resp = client.post("/users", json={"email": email, "name": name})
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture
def make_order(client):
    def _make(*, user_id: int, amount: str = "10.00", currency: str = "USD") -> dict:
        resp = client.post(
            "/orders",
            json={"user_id": user_id, "amount": amount, "currency": currency},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture
def user_with_orders(make_user, make_order):
    def _make(*, count: int = 5) -> tuple[dict, list[dict]]:
        user = make_user()
        orders = [
            make_order(user_id=user["id"], amount=f"{i+1}.00")
            for i in range(count)
        ]
        return user, orders

    return _make


@pytest.fixture
def assert_error_envelope():
    def _assert(resp, *, status: int, code: str) -> dict:
        assert resp.status_code == status, f"expected {status}, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert set(body.keys()) == {"error"}, body
        err = body["error"]
        assert err["status"] == status
        assert err["code"] == code
        assert isinstance(err["message"], str) and err["message"]
        datetime.fromisoformat(err["timestamp"])
        return err

    return _assert

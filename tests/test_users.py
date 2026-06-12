import uuid

import pytest


class TestCreateUser:
    def test_returns_201_on_valid_payload(self, client):
        resp = client.post(
            "/users",
            json={"email": "alice@example.com", "name": "Alice", "password": "TestPassword123!"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "alice@example.com"
        assert body["name"] == "Alice"
        assert isinstance(body["id"], int) and body["id"] > 0
        assert "created_at" in body
        assert "password" not in body and "password_hash" not in body

    def test_normalizes_email_and_name(self, client):
        resp = client.post(
            "/users",
            json={"email": "ALICE@Example.COM", "name": "  Alice  ", "password": "TestPassword123!"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "alice@example.com"
        assert body["name"] == "Alice"

    def test_returns_409_on_duplicate_email(self, client, assert_error_envelope):
        payload = {"email": "bob@example.com", "name": "Bob", "password": "TestPassword123!"}
        assert client.post("/users", json=payload).status_code == 201
        err = assert_error_envelope(
            client.post("/users", json=payload),
            status=409,
            code="conflict",
        )
        assert "exists" in err["message"].lower()

    def test_returns_409_on_duplicate_email_different_casing(self, client, assert_error_envelope):
        first = {"email": "carol@example.com", "name": "Carol", "password": "TestPassword123!"}
        second = {"email": "CAROL@example.com", "name": "Carol", "password": "TestPassword123!"}
        assert client.post("/users", json=first).status_code == 201
        assert_error_envelope(
            client.post("/users", json=second),
            status=409,
            code="conflict",
        )

    @pytest.mark.parametrize(
        "payload, bad_field",
        [
            ({"email": "not_an_email", "name": "Test"}, "email"),
            ({"email": "test@example.com", "name": " "}, "name"),
            ({"email": "test@example.com", "name": ""}, "name"),
            ({"email": "test@example.com", "name": "x" * 256}, "name"),
            ({"email": "test@example.com"}, "name"),
            ({"name": "Test"}, "email"),
            ({}, "email"),
        ],
        ids=[
            "invalid_email_format",
            "whitespace_only_name",
            "empty_name",
            "name_too_long",
            "missing_name",
            "missing_email",
            "empty_payload",
        ],
    )
    def test_invalid_payload_returns_422(self, client, assert_error_envelope, payload, bad_field):
        err = assert_error_envelope(
            client.post("/users", json=payload),
            status=422,
            code="validation_error",
        )
        assert any(
            d["field"] == bad_field for d in err["details"]["errors"]
        ), f"expected error on '{bad_field}', got {err['details']}"


class TestGetUser:
    def test_returns_user_when_exists(self, client, make_user):
        created = make_user(email="bob@test.com", name="Bob")
        resp = client.get(f"/users/{created['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created["id"]
        assert body["email"] == "bob@test.com"
        assert body["name"] == "Bob"

    def test_returns_404_when_not_found(self, client, assert_error_envelope):
        assert_error_envelope(
            client.get("/users/999999"),
            status=404,
            code="not_found",
        )

    def test_returns_422_when_id_not_int(self, client, assert_error_envelope):
        assert_error_envelope(
            client.get("/users/not-a-number"),
            status=422,
            code="validation_error",
        )


class TestFixtureSmoke:
    """Sanity-check that test isolation actually works."""

    def test_no_users_at_start_of_test_a(self, make_user):
        make_user(email=f"a-{uuid.uuid4()}@example.com")

    def test_no_users_at_start_of_test_b(self, make_user):
        # Re-creating the same email across tests would 409 if truncate didn't run.
        make_user(email="shared@example.com")

    def test_no_users_at_start_of_test_c(self, make_user):
        make_user(email="shared@example.com")

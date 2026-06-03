import pytest


class TestCreateOrder:
    def test_returns_201_on_valid_payload(self, client, make_user):
        user = make_user()
        resp = client.post(
            "/orders",
            json={"user_id": user["id"], "amount": "99.99", "currency": "USD"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["user_id"] == user["id"]
        assert body["amount"] == "99.99"
        assert body["currency"] == "USD"
        assert body["status"] == "pending"
        assert isinstance(body["id"], int) and body["id"] > 0
        assert "created_at" in body

    def test_returns_404_when_user_does_not_exist(self, client, assert_error_envelope):
        err = assert_error_envelope(
            client.post(
                "/orders",
                json={"user_id": 999999, "amount": "99.99", "currency": "USD"},
            ),
            status=404,
            code="not_found",
        )
        assert "999999" in err["message"]

    @pytest.mark.parametrize(
        "payload_override, bad_field",
        [
            ({"amount": "-1"}, "amount"),
            ({"amount": "0"}, "amount"),
            ({"amount": "abc"}, "amount"),
            ({"amount": "1.999"}, "amount"),
            ({"currency": "US"}, "currency"),
            ({"currency": "USDD"}, "currency"),
            ({"currency": ""}, "currency"),
            ({"user_id": "abc"}, "user_id"),
            ({"user_id": None}, "user_id"),
        ],
        ids=[
            "negative_amount",
            "zero_amount",
            "non_numeric_amount",
            "too_many_decimals",
            "currency_too_short",
            "currency_too_long",
            "empty_currency",
            "user_id_not_int",
            "user_id_null",
        ],
    )
    def test_invalid_payload_returns_422(
        self, client, make_user, assert_error_envelope, payload_override, bad_field
    ):
        user = make_user()
        payload = {"user_id": user["id"], "amount": "10.00", "currency": "USD"} | payload_override
        err = assert_error_envelope(
            client.post("/orders", json=payload),
            status=422,
            code="validation_error",
        )
        assert any(
            d["field"] == bad_field for d in err["details"]["errors"]
        ), f"expected error on '{bad_field}', got {err['details']}"


class TestGetOrder:
    def test_returns_order_when_exists(self, client, make_user, make_order):
        user = make_user()
        created = make_order(user_id=user["id"], amount="42.00")
        resp = client.get(f"/orders/{created['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created["id"]
        assert body["user_id"] == user["id"]
        assert body["amount"] == "42.00"

    def test_returns_404_when_not_found(self, client, assert_error_envelope):
        assert_error_envelope(
            client.get("/orders/999999"),
            status=404,
            code="not_found",
        )


class TestListOrders:
    def test_returns_empty_envelope_when_no_orders(self, client, make_user):
        user = make_user()
        resp = client.get(f"/users/{user['id']}/orders")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["pagination"] == {
            "limit": 20,
            "offset": 0,
            "total": 0,
            "has_more": False,
        }

    def test_first_page_offset_pagination(self, client, user_with_orders):
        user, _ = user_with_orders(count=5)
        resp = client.get(f"/users/{user['id']}/orders?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["pagination"] == {
            "limit": 2,
            "offset": 0,
            "total": 5,
            "has_more": True,
        }

    def test_last_page_has_more_false(self, client, user_with_orders):
        user, _ = user_with_orders(count=5)
        resp = client.get(f"/users/{user['id']}/orders?limit=2&offset=4")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["pagination"]["has_more"] is False
        assert body["pagination"]["total"] == 5

    def test_orders_are_returned_newest_first(self, client, user_with_orders):
        user, _ = user_with_orders(count=3)
        resp = client.get(f"/users/{user['id']}/orders")
        ids = [item["id"] for item in resp.json()["items"]]
        assert ids == sorted(ids, reverse=True)

    def test_does_not_leak_other_users_orders(self, client, make_user, make_order):
        alice = make_user(name="Alice")
        bob = make_user(name="Bob")
        make_order(user_id=alice["id"], amount="1.00")
        make_order(user_id=bob["id"], amount="2.00")
        make_order(user_id=bob["id"], amount="3.00")

        resp = client.get(f"/users/{alice['id']}/orders")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["amount"] == "1.00"
        assert body["pagination"]["total"] == 1

    def test_returns_404_when_user_does_not_exist(self, client, assert_error_envelope):
        assert_error_envelope(
            client.get("/users/999999/orders"),
            status=404,
            code="not_found",
        )

    @pytest.mark.parametrize(
        "query",
        ["limit=0", "limit=21", "offset=-1"],
        ids=["limit_zero", "limit_above_max", "negative_offset"],
    )
    def test_invalid_pagination_params_return_422(
        self, client, make_user, assert_error_envelope, query
    ):
        user = make_user()
        assert_error_envelope(
            client.get(f"/users/{user['id']}/orders?{query}"),
            status=422,
            code="validation_error",
        )


class TestListOrdersCursor:
    def test_first_page_without_cursor(self, client, user_with_orders):
        user, _ = user_with_orders(count=5)
        resp = client.get(f"/users/{user['id']}/orders/cursor?limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["pagination"]["limit"] == 2
        assert body["pagination"]["next_cursor"] is not None
        assert body["pagination"]["has_more"] is True

    def test_subsequent_page_with_cursor(self, client, user_with_orders):
        user, _ = user_with_orders(count=5)
        first = client.get(f"/users/{user['id']}/orders/cursor?limit=2").json()
        next_cursor = first["pagination"]["next_cursor"]

        resp = client.get(f"/users/{user['id']}/orders/cursor?limit=2&cursor={next_cursor}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert all(item["id"] < next_cursor for item in body["items"])

    def test_next_cursor_none_when_results_exhausted(self, client, user_with_orders):
        user, _ = user_with_orders(count=3)
        resp = client.get(f"/users/{user['id']}/orders/cursor?limit=10")
        body = resp.json()
        assert len(body["items"]) == 3
        assert body["pagination"]["next_cursor"] is None
        assert body["pagination"]["has_more"] is False

    def test_returns_empty_when_cursor_past_all_orders(self, client, user_with_orders):
        user, _ = user_with_orders(count=3)
        resp = client.get(f"/users/{user['id']}/orders/cursor?cursor=0&limit=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["pagination"]["next_cursor"] is None
        assert body["pagination"]["has_more"] is False

    def test_returns_desc_order_by_id(self, client, user_with_orders):
        user, _ = user_with_orders(count=3)
        body = client.get(f"/users/{user['id']}/orders/cursor?limit=10").json()
        ids = [item["id"] for item in body["items"]]
        assert ids == sorted(ids, reverse=True)

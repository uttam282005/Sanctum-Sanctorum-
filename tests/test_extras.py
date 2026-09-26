import concurrent.futures
import pytest


class TestListMembersExtra:
    def test_list_members_empty(self, client):
        response = client.get("/members")
        assert response.status_code == 200
        body = response.json()
        assert body == {"items": [], "total": 0, "limit": 20, "offset": 0}

    def test_list_members_pagination(self, client, make_member):
        members = [make_member(name=f"Member {i}", email=f"m{i}@example.com") for i in range(5)]
        response = client.get("/members", params={"limit": 2, "offset": 2})
        assert response.status_code == 200
        body = response.json()
        assert [m["id"] for m in body["items"]] == [members[2]["id"], members[3]["id"]]
        assert body["total"] == 5
        assert body["limit"] == 2
        assert body["offset"] == 2

    def test_default_limit_is_20(self, client, make_member):
        for i in range(25):
            make_member(name=f"Member {i}", email=f"m{i}@example.com")
        body = client.get("/members").json()
        assert len(body["items"]) == 20
        assert body["total"] == 25

    @pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
    def test_out_of_range_pagination_returns_422(self, client, params):
        assert client.get("/members", params=params).status_code == 422


class TestConcurrentOrdersExtra:
    def test_concurrent_orders_for_last_copy(self, client, make_member, make_book):
        book = make_book(stock=1)
        m1 = make_member(name="Member 1", email="m1@example.com")
        m2 = make_member(name="Member 2", email="m2@example.com")

        # Two simulated concurrent orders attempting to claim the single copy
        def place(member_id):
            return client.post("/orders", json={
                "member_id": member_id,
                "items": [{"book_id": book["id"], "quantity": 1}]
            })

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(place, m1["id"])
            f2 = executor.submit(place, m2["id"])
            res1 = f1.result()
            res2 = f2.result()

        statuses = sorted([res1.status_code, res2.status_code])
        # Exactly one should succeed with 201, and the other should fail with 409
        assert statuses == [201, 409]
        # Stock must be exactly 0, never negative
        book_res = client.get(f"/books/{book['id']}").json()
        assert book_res["stock"] == 0

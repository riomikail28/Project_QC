from unittest.mock import patch


def test_create_staff_does_not_send_full_name_to_staff_accounts():
    from backend.auth import staff_manager

    calls = []

    def fake_direct(table, method="GET", payload=None, filters=""):
        calls.append((table, method, payload, filters))
        if table == "staff_accounts" and method == "POST":
            assert "full_name" not in payload
            return [{"id": "staff-1", **payload}]
        if table == "users" and method == "GET":
            return []
        if table == "users" and method == "POST":
            assert payload["full_name"] == "Lala"
            assert payload["staff_account_id"] == "staff-1"
            return [{"id": "user-1", **payload}]
        return []

    with patch("backend.database.supabase_client.direct_db_query", side_effect=fake_direct):
        created = staff_manager.create_staff(
            {
                "username": "lala",
                "password": "secret123",
                "role": "staff",
                "full_name": "Lala",
            }
        )

    assert created["id"] == "staff-1"
    assert created["full_name"] == "Lala"
    assert "password_hash" not in created
    assert any(table == "users" and method == "POST" for table, method, _, _ in calls)


def test_update_staff_full_name_only_updates_users_profile():
    from backend.auth import staff_manager

    calls = []

    def fake_direct(table, method="GET", payload=None, filters=""):
        calls.append((table, method, payload, filters))
        if table == "staff_accounts" and method == "GET":
            return [{"id": "staff-1", "username": "lala", "role": "staff"}]
        if table == "users" and method == "GET":
            return [{"id": "user-1", "staff_account_id": "staff-1", "full_name": "Old"}]
        if table == "users" and method == "PATCH":
            assert payload["full_name"] == "New Name"
            return [{"id": "user-1", **payload}]
        return []

    with patch("backend.database.supabase_client.direct_db_query", side_effect=fake_direct):
        updated = staff_manager.update_staff("staff-1", {"full_name": "New Name"})

    assert updated["full_name"] == "New Name"
    assert not any(table == "staff_accounts" and method == "PATCH" for table, method, _, _ in calls)

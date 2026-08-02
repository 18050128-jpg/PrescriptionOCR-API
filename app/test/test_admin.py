"""
test_admin.py — luồng quản trị: list/get/role/toggle/delete users, stats.
"""

import uuid
import pytest
from app.test.conftest import (
    auth_headers, register_user, upload_prescription,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_user_id(client, token: str) -> str:
    data = client.get("/api/v1/auth/me",
                      headers=auth_headers(token)).json()
    return data.get("_id") or data.get("id", "")


# ---------------------------------------------------------------------------
# List users
# ---------------------------------------------------------------------------

class TestAdminListUsers:
    def test_admin_gets_all_users(self, client, admin_token, user_token, user2_token):
        r = client.get("/api/v1/admin/users",
                       headers=auth_headers(admin_token))
        assert r.status_code == 200
        assert r.json()["total"] == 3  # admin + user1 + user2

    def test_hashed_password_not_exposed(self, client, admin_token):
        r = client.get("/api/v1/admin/users",
                       headers=auth_headers(admin_token))
        for user in r.json()["users"]:
            assert "hashed_password" not in user

    def test_regular_user_cannot_list_users(self, client, user_token):
        r = client.get("/api/v1/admin/users",
                       headers=auth_headers(user_token))
        assert r.status_code == 403

    def test_unauthenticated_cannot_list(self, client):
        r = client.get("/api/v1/admin/users")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Get single user
# ---------------------------------------------------------------------------

class TestAdminGetUser:
    def test_get_existing_user(self, client, admin_token, user_token):
        uid = get_user_id(client, user_token)
        r = client.get(f"/api/v1/admin/users/{uid}",
                       headers=auth_headers(admin_token))
        assert r.status_code == 200
        assert r.json()["_id"] == uid
        assert "hashed_password" not in r.json()

    def test_get_nonexistent_user_returns_404(self, client, admin_token):
        r = client.get("/api/v1/admin/users/ghost-id",
                       headers=auth_headers(admin_token))
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Update role
# ---------------------------------------------------------------------------

class TestAdminUpdateRole:
    def test_promote_user_to_admin(self, client, admin_token, user_token):
        uid = get_user_id(client, user_token)
        r = client.put(f"/api/v1/admin/users/{uid}/role",
                       json={"role": "admin"},
                       headers=auth_headers(admin_token))
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"

    def test_demote_admin_to_user(self, client, admin_token, user_token):
        uid = get_user_id(client, user_token)
        # Trước tiên promote
        client.put(f"/api/v1/admin/users/{uid}/role",
                   json={"role": "admin"},
                   headers=auth_headers(admin_token))
        # Sau đó demote
        r = client.put(f"/api/v1/admin/users/{uid}/role",
                       json={"role": "user"},
                       headers=auth_headers(admin_token))
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "user"

    def test_admin_cannot_demote_self(self, client, admin_token):
        uid = get_user_id(client, admin_token)
        r = client.put(f"/api/v1/admin/users/{uid}/role",
                       json={"role": "user"},
                       headers=auth_headers(admin_token))
        assert r.status_code == 400

    def test_invalid_role_rejected(self, client, admin_token, user_token):
        uid = get_user_id(client, user_token)
        r = client.put(f"/api/v1/admin/users/{uid}/role",
                       json={"role": "superadmin"},
                       headers=auth_headers(admin_token))
        assert r.status_code == 400

    def test_regular_user_cannot_change_roles(self, client, user_token, user2_token):
        uid = get_user_id(client, user2_token)
        r = client.put(f"/api/v1/admin/users/{uid}/role",
                       json={"role": "admin"},
                       headers=auth_headers(user_token))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Toggle active
# ---------------------------------------------------------------------------

class TestAdminToggleActive:
    def test_disable_user(self, client, admin_token, user_token):
        uid = get_user_id(client, user_token)
        r = client.put(f"/api/v1/admin/users/{uid}/toggle-active",
                       headers=auth_headers(admin_token))
        assert r.status_code == 200
        assert r.json()["user"]["is_active"] is False

    def test_re_enable_user(self, client, admin_token, user_token):
        uid = get_user_id(client, user_token)
        # Tắt
        client.put(f"/api/v1/admin/users/{uid}/toggle-active",
                   headers=auth_headers(admin_token))
        # Bật lại
        r = client.put(f"/api/v1/admin/users/{uid}/toggle-active",
                       headers=auth_headers(admin_token))
        assert r.json()["user"]["is_active"] is True

    def test_admin_cannot_disable_self(self, client, admin_token):
        uid = get_user_id(client, admin_token)
        r = client.put(f"/api/v1/admin/users/{uid}/toggle-active",
                       headers=auth_headers(admin_token))
        assert r.status_code == 400

    def test_disabled_user_request_returns_400(self, client, admin_token, user_token):
        uid = get_user_id(client, user_token)
        client.put(f"/api/v1/admin/users/{uid}/toggle-active",
                   headers=auth_headers(admin_token))
        # User bị tắt cố gọi API
        r = client.get("/api/v1/auth/me",
                       headers=auth_headers(user_token))
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Delete user (cascade)
# ---------------------------------------------------------------------------

class TestAdminDeleteUser:
    def test_delete_user_removes_account(self, client, admin_token, user_token):
        uid = get_user_id(client, user_token)
        r = client.delete(f"/api/v1/admin/users/{uid}",
                          headers=auth_headers(admin_token))
        assert r.status_code == 200
        # Kiểm tra user đã biến mất
        r2 = client.get(f"/api/v1/admin/users/{uid}",
                        headers=auth_headers(admin_token))
        assert r2.status_code == 404

    def test_delete_cascades_prescriptions(self, client, admin_token,
                                           user_token, prescription):
        """Xóa user → prescription của user cũng bị xóa."""
        uid = get_user_id(client, user_token)
        presc_id = prescription["_id"]

        client.delete(f"/api/v1/admin/users/{uid}",
                      headers=auth_headers(admin_token))

        # Admin thử lấy prescription → 404
        r = client.get(f"/api/v1/prescriptions/{presc_id}",
                       headers=auth_headers(admin_token))
        assert r.status_code == 404

    def test_delete_cascades_reminders(self, client, admin_token,
                                       user_token, reminder):
        """Xóa user → reminder của user cũng bị xóa."""
        uid = get_user_id(client, user_token)
        rem_id = reminder["_id"]

        client.delete(f"/api/v1/admin/users/{uid}",
                      headers=auth_headers(admin_token))

        r = client.get(f"/api/v1/reminders/{rem_id}",
                       headers=auth_headers(admin_token))
        assert r.status_code == 404

    def test_admin_cannot_delete_self(self, client, admin_token):
        uid = get_user_id(client, admin_token)
        r = client.delete(f"/api/v1/admin/users/{uid}",
                          headers=auth_headers(admin_token))
        assert r.status_code == 400

    def test_delete_nonexistent_returns_404(self, client, admin_token):
        r = client.delete("/api/v1/admin/users/ghost-id",
                          headers=auth_headers(admin_token))
        assert r.status_code == 404

    def test_regular_user_cannot_delete_users(self, client, user_token, user2_token):
        uid = get_user_id(client, user2_token)
        r = client.delete(f"/api/v1/admin/users/{uid}",
                          headers=auth_headers(user_token))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Create admin
# ---------------------------------------------------------------------------

class TestAdminCreateAdmin:
    def test_admin_can_create_new_admin_account(self, client, admin_token):
        r = client.post(
            "/api/v1/admin/users/create-admin",
            json={
                "username": "newadmin",
                "email": "newadmin@example.com",
                "password": "secret123",
                "full_name": "New Admin",
            },
            headers=auth_headers(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "success"
        assert r.json()["user"]["role"] == "admin"


# ---------------------------------------------------------------------------
# Admin: list all prescriptions
# ---------------------------------------------------------------------------

class TestAdminListPrescriptions:
    def test_admin_sees_all_prescriptions(self, client, admin_token,
                                          user_token, user2_token):
        upload_prescription(client, user_token)
        upload_prescription(client, user2_token)

        r = client.get("/api/v1/admin/prescriptions",
                       headers=auth_headers(admin_token))
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_regular_user_cannot_list_all(self, client, user_token):
        r = client.get("/api/v1/admin/prescriptions",
                       headers=auth_headers(user_token))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestAdminStats:
    def test_stats_returns_correct_counts(self, client, admin_token,
                                          user_token, prescription, reminder):
        r = client.get("/api/v1/admin/stats",
                       headers=auth_headers(admin_token))
        assert r.status_code == 200
        body = r.json()
        assert body["total_users"] == 2        # admin + user1
        assert body["total_prescriptions"] == 1
        assert body["total_reminders"] == 1
        assert "total_notifications" in body

    def test_stats_requires_admin(self, client, user_token):
        r = client.get("/api/v1/admin/stats",
                       headers=auth_headers(user_token))
        assert r.status_code == 403

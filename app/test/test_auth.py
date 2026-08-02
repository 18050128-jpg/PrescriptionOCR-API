"""
test_auth.py — luồng xác thực: đăng ký, đăng nhập, /me, phân quyền.
"""

import pytest
from app.test.conftest import register_user, login_user, auth_headers


# ---------------------------------------------------------------------------
# Đăng ký
# ---------------------------------------------------------------------------

class TestRegister:
    def test_first_user_becomes_admin(self, client):
        data = register_user(client, "first", email="first@x.com")
        assert data["user"]["role"] == "admin"

    def test_second_user_is_regular(self, client):
        register_user(client, "admin_u", email="a@x.com")
        data = register_user(client, "normal_u", email="n@x.com")
        assert data["user"]["role"] == "user"

    def test_register_returns_token(self, client):
        data = register_user(client)
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_returns_user_info(self, client):
        data = register_user(client, "alice", email="alice@x.com",
                             full_name="Alice Nguyen")
        user = data["user"]
        assert user["username"] == "alice"
        assert user["email"] == "alice@x.com"
        assert user["full_name"] == "Alice Nguyen"
        assert "hashed_password" not in user

    def test_duplicate_username_rejected(self, client):
        register_user(client)
        r = client.post("/api/v1/auth/register",
                        json={"username": "testuser", "password": "pass123",
                              "email": "other@x.com"})
        assert r.status_code == 400
        assert "Username" in r.json()["detail"]

    def test_duplicate_email_rejected(self, client):
        register_user(client, email="same@x.com")
        r = client.post("/api/v1/auth/register",
                        json={"username": "other", "password": "pass123",
                              "email": "same@x.com"})
        assert r.status_code == 400
        assert "Email" in r.json()["detail"]

    def test_short_username_rejected(self, client):
        r = client.post("/api/v1/auth/register",
                        json={"username": "ab", "password": "pass123",
                              "email": "ab@x.com"})
        assert r.status_code == 422

    def test_short_password_rejected(self, client):
        r = client.post("/api/v1/auth/register",
                        json={"username": "valid_u", "password": "12345",
                              "email": "v@x.com"})
        assert r.status_code == 422

    def test_invalid_email_rejected(self, client):
        r = client.post("/api/v1/auth/register",
                        json={"username": "valid_u", "password": "pass123",
                              "email": "not-an-email"})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Đăng nhập
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_returns_token_and_user(self, client):
        register_user(client, "usr1", email="u1@x.com")
        r = client.post("/api/v1/auth/login",
                        data={"username": "usr1", "password": "pass123"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["user"]["username"] == "usr1"

    def test_wrong_password_rejected(self, client):
        register_user(client)
        r = client.post("/api/v1/auth/login",
                        data={"username": "testuser", "password": "wrongpass"})
        assert r.status_code == 401

    def test_nonexistent_user_rejected(self, client):
        r = client.post("/api/v1/auth/login",
                        data={"username": "ghost", "password": "pass123"})
        assert r.status_code == 401

    def test_disabled_user_cannot_login(self, client, admin_token):
        # Đăng ký user2
        data = register_user(client, "u_dis", email="dis@x.com")
        uid = data["user"].get("_id") or data["user"].get("id", "")
        # Admin vô hiệu hoá
        client.put(f"/api/v1/admin/users/{uid}/toggle-active",
                   headers=auth_headers(admin_token))
        # User cố đăng nhập
        r = client.post("/api/v1/auth/login",
                        data={"username": "u_dis", "password": "pass123"})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------

class TestMe:
    def test_me_returns_current_user(self, client, user_token):
        r = client.get("/api/v1/auth/me",
                       headers=auth_headers(user_token))
        assert r.status_code == 200
        assert r.json()["username"] == "user1"

    def test_me_without_token_is_401(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_me_invalid_token_is_401(self, client):
        r = client.get("/api/v1/auth/me",
                       headers={"Authorization": "Bearer garbage.token.here"})
        assert r.status_code == 401

    def test_update_me_fullname(self, client, user_token):
        r = client.put("/api/v1/auth/me",
                       json={"full_name": "Nguyen Van A"},
                       headers=auth_headers(user_token))
        assert r.status_code == 200
        assert r.json()["full_name"] == "Nguyen Van A"

    def test_update_me_ignores_unknown_fields(self, client, user_token):
        r = client.put("/api/v1/auth/me",
                       json={"role": "admin"},       # không được phép
                       headers=auth_headers(user_token))
        # Nếu không có trường hợp lệ → 400
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Phân quyền admin tự động
# ---------------------------------------------------------------------------

class TestAutoAdmin:
    def test_only_first_is_admin(self, client):
        users = []
        for i in range(4):
            data = register_user(client, f"usr{i}", email=f"usr{i}@x.com")
            users.append(data["user"])

        assert users[0]["role"] == "admin"
        for u in users[1:]:
            assert u["role"] == "user"

    def test_admin_can_access_admin_routes(self, client, admin_token):
        r = client.get("/api/v1/admin/users",
                       headers=auth_headers(admin_token))
        assert r.status_code == 200

    def test_user_cannot_access_admin_routes(self, client, user_token):
        r = client.get("/api/v1/admin/users",
                       headers=auth_headers(user_token))
        assert r.status_code == 403

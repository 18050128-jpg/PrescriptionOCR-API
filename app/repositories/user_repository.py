"""
Repository layer cho User — toàn bộ CRUD users đi qua đây.
"""

import uuid
from datetime import datetime

from app.database import json_store

COLLECTION = "users"


def create(username: str, email: str, hashed_password: str,
           full_name: str | None = None, role: str = "user") -> dict:
    """Tạo user mới. Trả về document đã lưu."""
    document = {
        "_id":             str(uuid.uuid4()),
        "created_at":      datetime.now().isoformat(timespec="seconds"),
        "username":        username,
        "email":           email,
        "hashed_password": hashed_password,
        "full_name":       full_name,
        "role":            role,
        "is_active":       True,
    }
    return json_store.insert(COLLECTION, document)


def get_all() -> list[dict]:
    """Lấy toàn bộ users, mới nhất lên đầu."""
    records = json_store.find_all(COLLECTION)
    return sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)


def get_by_id(user_id: str) -> dict | None:
    return json_store.find_by_id(COLLECTION, user_id)


def get_by_username(username: str) -> dict | None:
    return json_store.find_one_by_field(COLLECTION, "username", username)


def get_by_email(email: str) -> dict | None:
    return json_store.find_one_by_field(COLLECTION, "email", email)


def update(user_id: str, updates: dict) -> dict | None:
    return json_store.update_by_id(COLLECTION, user_id, updates)


def delete(user_id: str) -> bool:
    return json_store.delete_by_id(COLLECTION, user_id)


def total() -> int:
    return json_store.count(COLLECTION)


def exists_any() -> bool:
    """Kiểm tra xem đã có user nào chưa (dùng để tạo admin đầu tiên)."""
    return json_store.count(COLLECTION) > 0

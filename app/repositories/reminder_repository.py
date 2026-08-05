"""
Repository layer cho Reminder.
"""

import uuid
from datetime import datetime

from app.database import json_store

COLLECTION = "reminders"


def create(user_id: str, prescription_id: str, medicine_name: str,
           remind_time: str, days_of_week: list[int] | None = None,
           note: str | None = None) -> dict:
    """Tạo reminder mới."""
    document = {
        "_id":             str(uuid.uuid4()),
        "created_at":      datetime.now().isoformat(timespec="seconds"),
        "user_id":         user_id,
        "prescription_id": prescription_id,
        "medicine_name":   medicine_name,
        "remind_time":     remind_time,        # "HH:MM"
        "days_of_week":    days_of_week or [],  # [] = mỗi ngày
        "note":            note,
        "is_active":       True,
    }
    return json_store.insert(COLLECTION, document)


def get_all() -> list[dict]:
    return json_store.find_all(COLLECTION)


def get_by_user(user_id: str) -> list[dict]:
    """Lấy tất cả reminders của một user."""
    records = json_store.find_by_field(COLLECTION, "user_id", user_id)
    return sorted(records, key=lambda r: r.get("remind_time", ""))


def get_by_prescription(prescription_id: str) -> list[dict]:
    return json_store.find_by_field(COLLECTION, "prescription_id", prescription_id)


def get_by_id(reminder_id: str) -> dict | None:
    return json_store.find_by_id(COLLECTION, reminder_id)


def update(reminder_id: str, updates: dict) -> dict | None:
    return json_store.update_by_id(COLLECTION, reminder_id, updates)


def delete(reminder_id: str) -> bool:
    return json_store.delete_by_id(COLLECTION, reminder_id)


def get_active_reminders() -> list[dict]:
    """Lấy tất cả reminders đang bật (is_active=True)."""
    return [r for r in json_store.find_all(COLLECTION) if r.get("is_active", True)]

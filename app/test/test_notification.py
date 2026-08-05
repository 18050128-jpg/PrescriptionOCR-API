"""
test_notification.py — kiểm tra luồng tạo thông báo tự động và quản lý notification.
"""

import uuid
from datetime import datetime

import pytest
import pytz

from app.database import json_store
from app.services.reminder_scheduler import check_reminders
from app.test.conftest import auth_headers


LOCAL_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
NOTIF_COLLECTION = "notifications"


# ---------------------------------------------------------------------------
# Helper: tạo reminder thẳng trong store (bypass API để test scheduler)
# ---------------------------------------------------------------------------

def _insert_reminder(data_dir, user_id: str, prescription_id: str,
                     remind_time: str, days_of_week: list[int] | None = None,
                     is_active: bool = True) -> dict:
    doc = {
        "_id":             str(uuid.uuid4()),
        "created_at":      datetime.now().isoformat(timespec="seconds"),
        "user_id":         user_id,
        "prescription_id": prescription_id,
        "medicine_name":   "TEST_MED",
        "remind_time":     remind_time,
        "days_of_week":    days_of_week or [],
        "is_active":       is_active,
        "note":            None,
    }
    json_store.insert("reminders", doc)
    return doc


# ---------------------------------------------------------------------------
# Scheduler: check_reminders()
# ---------------------------------------------------------------------------

class TestSchedulerCheckReminders:
    def test_creates_notification_when_time_matches(self, data_dir, monkeypatch):
        """Khi remind_time khớp giờ hiện tại → tạo notification."""
        user_id = str(uuid.uuid4())
        now = datetime.now(LOCAL_TZ)
        current_time = now.strftime("%H:%M")

        _insert_reminder(data_dir, user_id, "presc-1", current_time)

        check_reminders()

        notifs = json_store.find_by_field(NOTIF_COLLECTION, "user_id", user_id)
        assert len(notifs) == 1
        notif = notifs[0]
        assert notif["is_read"] is False
        assert "TEST_MED" in notif["message"]
        assert notif["remind_time"] == current_time

    def test_no_notification_when_time_does_not_match(self, data_dir):
        """Khi remind_time KHÔNG khớp → không tạo notification."""
        user_id = str(uuid.uuid4())
        _insert_reminder(data_dir, user_id, "presc-1", "03:47")  # giờ rất khó khớp

        # Giả sử giờ hiện tại không phải 03:47
        now_str = datetime.now(LOCAL_TZ).strftime("%H:%M")
        if now_str == "03:47":
            pytest.skip("Test chạy đúng lúc 03:47 — bỏ qua")

        check_reminders()

        notifs = json_store.find_by_field(NOTIF_COLLECTION, "user_id", user_id)
        assert len(notifs) == 0

    def test_inactive_reminder_skipped(self, data_dir):
        """Reminder bị tắt (is_active=False) không tạo notification."""
        user_id = str(uuid.uuid4())
        now_time = datetime.now(LOCAL_TZ).strftime("%H:%M")

        _insert_reminder(data_dir, user_id, "presc-1", now_time, is_active=False)

        check_reminders()

        notifs = json_store.find_by_field(NOTIF_COLLECTION, "user_id", user_id)
        assert len(notifs) == 0

    def test_days_of_week_filter(self, data_dir, monkeypatch):
        """Reminder chỉ áp dụng ngày nhất định — không chạy ngày khác."""
        user_id = str(uuid.uuid4())
        now = datetime.now(LOCAL_TZ)
        now_time = now.strftime("%H:%M")
        today = now.weekday()          # 0–6
        wrong_day = (today + 1) % 7   # ngày khác hôm nay

        _insert_reminder(data_dir, user_id, "presc-1", now_time,
                         days_of_week=[wrong_day])

        check_reminders()

        notifs = json_store.find_by_field(NOTIF_COLLECTION, "user_id", user_id)
        assert len(notifs) == 0

    def test_days_of_week_includes_today(self, data_dir):
        """Reminder áp dụng đúng ngày hôm nay → tạo notification."""
        user_id = str(uuid.uuid4())
        now = datetime.now(LOCAL_TZ)
        now_time = now.strftime("%H:%M")
        today = now.weekday()

        _insert_reminder(data_dir, user_id, "presc-1", now_time,
                         days_of_week=[today])

        check_reminders()

        notifs = json_store.find_by_field(NOTIF_COLLECTION, "user_id", user_id)
        assert len(notifs) == 1

    def test_multiple_reminders_same_time(self, data_dir):
        """Nhiều reminder cùng giờ → tạo nhiều notification."""
        now_time = datetime.now(LOCAL_TZ).strftime("%H:%M")
        user_ids = [str(uuid.uuid4()) for _ in range(3)]

        for uid in user_ids:
            _insert_reminder(data_dir, uid, "presc-x", now_time)

        check_reminders()

        for uid in user_ids:
            notifs = json_store.find_by_field(NOTIF_COLLECTION, "user_id", uid)
            assert len(notifs) == 1

    def test_notification_structure(self, data_dir):
        """Kiểm tra cấu trúc đầy đủ của notification document."""
        user_id = str(uuid.uuid4())
        presc_id = str(uuid.uuid4())
        now_time = datetime.now(LOCAL_TZ).strftime("%H:%M")

        rem = _insert_reminder(data_dir, user_id, presc_id, now_time)
        check_reminders()

        notif = json_store.find_by_field(NOTIF_COLLECTION, "user_id", user_id)[0]
        assert notif["user_id"] == user_id
        assert notif["prescription_id"] == presc_id
        assert notif["reminder_id"] == rem["_id"]
        assert notif["medicine_name"] == "TEST_MED"
        assert notif["is_read"] is False
        assert "_id" in notif
        assert "created_at" in notif
        assert "message" in notif


# ---------------------------------------------------------------------------
# Notification API
# ---------------------------------------------------------------------------

class TestNotificationAPI:
    def test_list_notifications_empty(self, client, user_token):
        r = client.get("/api/v1/notifications/",
                       headers=auth_headers(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["unread"] == 0

    def test_list_notifications_requires_auth(self, client):
        r = client.get("/api/v1/notifications/")
        assert r.status_code == 401

    def test_user_sees_only_own_notifications(self, client, data_dir,
                                              user_token, user2_token):
        """Chèn notification trực tiếp vào store cho 2 users."""
        me = client.get("/api/v1/auth/me",
                        headers=auth_headers(user_token)).json()
        me2 = client.get("/api/v1/auth/me",
                         headers=auth_headers(user2_token)).json()
        me_id  = me.get("_id")  or me.get("id",  "")
        me2_id = me2.get("_id") or me2.get("id", "")

        # Tạo 2 notif cho user1, 1 notif cho user2
        for i in range(2):
            json_store.insert(NOTIF_COLLECTION, {
                "_id": str(uuid.uuid4()), "created_at": "2025-01-01T08:00:00",
                "user_id": me_id, "reminder_id": "r", "prescription_id": "p",
                "medicine_name": "MED", "remind_time": "08:00",
                "message": "test", "is_read": False,
            })
        json_store.insert(NOTIF_COLLECTION, {
            "_id": str(uuid.uuid4()), "created_at": "2025-01-01T08:00:00",
            "user_id": me2_id, "reminder_id": "r", "prescription_id": "p",
            "medicine_name": "MED", "remind_time": "08:00",
            "message": "test", "is_read": False,
        })

        r1 = client.get("/api/v1/notifications/",
                        headers=auth_headers(user_token))
        r2 = client.get("/api/v1/notifications/",
                        headers=auth_headers(user2_token))

        assert r1.json()["total"] == 2
        assert r2.json()["total"] == 1

    def test_unread_count(self, client, data_dir, user_token):
        me = client.get("/api/v1/auth/me",
                        headers=auth_headers(user_token)).json()
        me_id = me.get("_id") or me.get("id", "")
        for is_read in [False, False, True]:
            json_store.insert(NOTIF_COLLECTION, {
                "_id": str(uuid.uuid4()), "created_at": "2025-01-01T08:00:00",
                "user_id": me_id, "reminder_id": "r", "prescription_id": "p",
                "medicine_name": "MED", "remind_time": "08:00",
                "message": "msg", "is_read": is_read,
            })
        r = client.get("/api/v1/notifications/",
                       headers=auth_headers(user_token))
        assert r.json()["unread"] == 2

    def test_mark_as_read(self, client, data_dir, user_token):
        me = client.get("/api/v1/auth/me",
                        headers=auth_headers(user_token)).json()
        me_id = me.get("_id") or me.get("id", "")
        notif_id = str(uuid.uuid4())
        json_store.insert(NOTIF_COLLECTION, {
            "_id": notif_id, "created_at": "2025-01-01T08:00:00",
            "user_id": me_id, "reminder_id": "r", "prescription_id": "p",
            "medicine_name": "MED", "remind_time": "08:00",
            "message": "msg", "is_read": False,
        })
        r = client.put(f"/api/v1/notifications/{notif_id}/read",
                       headers=auth_headers(user_token))
        assert r.status_code == 200
        assert r.json()["notification"]["is_read"] is True

    def test_mark_all_as_read(self, client, data_dir, user_token):
        me = client.get("/api/v1/auth/me",
                        headers=auth_headers(user_token)).json()
        me_id = me.get("_id") or me.get("id", "")
        for _ in range(3):
            json_store.insert(NOTIF_COLLECTION, {
                "_id": str(uuid.uuid4()), "created_at": "2025-01-01T08:00:00",
                "user_id": me_id, "reminder_id": "r", "prescription_id": "p",
                "medicine_name": "MED", "remind_time": "08:00",
                "message": "msg", "is_read": False,
            })
        r = client.put("/api/v1/notifications/read-all",
                       headers=auth_headers(user_token))
        assert r.status_code == 200
        assert r.json()["marked_read"] == 3

        # Kiểm tra unread = 0
        r2 = client.get("/api/v1/notifications/",
                        headers=auth_headers(user_token))
        assert r2.json()["unread"] == 0

    def test_delete_notification(self, client, data_dir, user_token):
        me = client.get("/api/v1/auth/me",
                        headers=auth_headers(user_token)).json()
        me_id = me.get("_id") or me.get("id", "")
        notif_id = str(uuid.uuid4())
        json_store.insert(NOTIF_COLLECTION, {
            "_id": notif_id, "created_at": "2025-01-01T08:00:00",
            "user_id": me_id, "reminder_id": "r", "prescription_id": "p",
            "medicine_name": "MED", "remind_time": "08:00",
            "message": "msg", "is_read": False,
        })
        r = client.delete(f"/api/v1/notifications/{notif_id}",
                          headers=auth_headers(user_token))
        assert r.status_code == 200

        r2 = client.get("/api/v1/notifications/",
                        headers=auth_headers(user_token))
        assert r2.json()["total"] == 0

    def test_other_user_cannot_read_notification(self, client, data_dir,
                                                  user_token, user2_token):
        me = client.get("/api/v1/auth/me",
                        headers=auth_headers(user_token)).json()
        notif_id = str(uuid.uuid4())
        json_store.insert(NOTIF_COLLECTION, {
            "_id": notif_id, "created_at": "2025-01-01T08:00:00",
            "user_id": me["_id"], "reminder_id": "r", "prescription_id": "p",
            "medicine_name": "MED", "remind_time": "08:00",
            "message": "msg", "is_read": False,
        })
        # user2 cố đánh dấu đọc notification của user1
        r = client.put(f"/api/v1/notifications/{notif_id}/read",
                       headers=auth_headers(user2_token))
        assert r.status_code == 403

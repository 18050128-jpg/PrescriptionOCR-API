"""
test_reminder.py — CRUD reminder, validate giờ, validate prescription owner.
"""

import pytest
from app.test.conftest import auth_headers, upload_prescription


# ---------------------------------------------------------------------------
# Tạo reminder
# ---------------------------------------------------------------------------

class TestCreateReminder:
    def test_create_success(self, client, user_token, prescription):
        r = client.post(
            "/api/v1/reminders/",
            json={
                "prescription_id": prescription["_id"],
                "medicine_name":   "AMOXICILLIN",
                "remind_time":     "08:00",
                "days_of_week":    [],
            },
            headers=auth_headers(user_token),
        )
        assert r.status_code == 201
        rem = r.json()["reminder"]
        assert rem["remind_time"] == "08:00"
        assert rem["medicine_name"] == "AMOXICILLIN"
        assert rem["is_active"] is True

    def test_create_requires_auth(self, client, prescription):
        r = client.post(
            "/api/v1/reminders/",
            json={
                "prescription_id": prescription["_id"],
                "medicine_name":   "DRUG",
                "remind_time":     "09:00",
            },
        )
        assert r.status_code == 401

    def test_create_with_days_of_week(self, client, user_token, prescription):
        r = client.post(
            "/api/v1/reminders/",
            json={
                "prescription_id": prescription["_id"],
                "medicine_name":   "DRUG",
                "remind_time":     "21:00",
                "days_of_week":    [0, 2, 4],   # T2, T4, T6
            },
            headers=auth_headers(user_token),
        )
        assert r.status_code == 201
        assert r.json()["reminder"]["days_of_week"] == [0, 2, 4]

    def test_days_of_week_deduplicated(self, client, user_token, prescription):
        r = client.post(
            "/api/v1/reminders/",
            json={
                "prescription_id": prescription["_id"],
                "medicine_name":   "DRUG",
                "remind_time":     "07:00",
                "days_of_week":    [1, 1, 3, 3],
            },
            headers=auth_headers(user_token),
        )
        assert r.status_code == 201
        assert r.json()["reminder"]["days_of_week"] == [1, 3]

    def test_cannot_create_for_others_prescription(self, client,
                                                    user2_token, prescription):
        """user2 không thể tạo reminder cho toa của user1."""
        r = client.post(
            "/api/v1/reminders/",
            json={
                "prescription_id": prescription["_id"],
                "medicine_name":   "DRUG",
                "remind_time":     "10:00",
            },
            headers=auth_headers(user2_token),
        )
        assert r.status_code == 403

    def test_nonexistent_prescription_returns_404(self, client, user_token):
        r = client.post(
            "/api/v1/reminders/",
            json={
                "prescription_id": "does-not-exist",
                "medicine_name":   "DRUG",
                "remind_time":     "10:00",
            },
            headers=auth_headers(user_token),
        )
        assert r.status_code == 404

    # --- Validate remind_time ---

    def test_invalid_time_format_rejected(self, client, user_token, prescription):
        for bad_time in ["8:00", "08:60", "25:00", "abc", "8am"]:
            r = client.post(
                "/api/v1/reminders/",
                json={
                    "prescription_id": prescription["_id"],
                    "medicine_name":   "DRUG",
                    "remind_time":     bad_time,
                },
                headers=auth_headers(user_token),
            )
            assert r.status_code == 422, f"Expected 422 for time='{bad_time}'"

    def test_valid_boundary_times(self, client, user_token, prescription):
        for good_time in ["00:00", "23:59"]:
            r = client.post(
                "/api/v1/reminders/",
                json={
                    "prescription_id": prescription["_id"],
                    "medicine_name":   "DRUG",
                    "remind_time":     good_time,
                },
                headers=auth_headers(user_token),
            )
            assert r.status_code == 201, f"Expected 201 for time='{good_time}'"

    def test_invalid_day_of_week_rejected(self, client, user_token, prescription):
        r = client.post(
            "/api/v1/reminders/",
            json={
                "prescription_id": prescription["_id"],
                "medicine_name":   "DRUG",
                "remind_time":     "08:00",
                "days_of_week":    [7],   # 7 không hợp lệ
            },
            headers=auth_headers(user_token),
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# List reminders
# ---------------------------------------------------------------------------

class TestListReminders:
    def test_list_returns_own_reminders(self, client, reminder, user_token):
        r = client.get("/api/v1/reminders/",
                       headers=auth_headers(user_token))
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_user2_does_not_see_user1_reminders(self, client, reminder, user2_token):
        r = client.get("/api/v1/reminders/",
                       headers=auth_headers(user2_token))
        assert r.json()["total"] == 0

    def test_list_requires_auth(self, client):
        r = client.get("/api/v1/reminders/")
        assert r.status_code == 401

    def test_sorted_by_remind_time(self, client, user_token, prescription):
        for t in ["20:00", "06:00", "12:00"]:
            client.post(
                "/api/v1/reminders/",
                json={
                    "prescription_id": prescription["_id"],
                    "medicine_name":   "DRUG",
                    "remind_time":     t,
                },
                headers=auth_headers(user_token),
            )
        r = client.get("/api/v1/reminders/",
                       headers=auth_headers(user_token))
        times = [rem["remind_time"] for rem in r.json()["reminders"]]
        assert times == sorted(times)


# ---------------------------------------------------------------------------
# Get single reminder
# ---------------------------------------------------------------------------

class TestGetReminder:
    def test_owner_can_get(self, client, reminder, user_token):
        r = client.get(f"/api/v1/reminders/{reminder['_id']}",
                       headers=auth_headers(user_token))
        assert r.status_code == 200

    def test_other_user_gets_403(self, client, reminder, user2_token):
        r = client.get(f"/api/v1/reminders/{reminder['_id']}",
                       headers=auth_headers(user2_token))
        assert r.status_code == 403

    def test_admin_can_get_any(self, client, reminder, admin_token):
        r = client.get(f"/api/v1/reminders/{reminder['_id']}",
                       headers=auth_headers(admin_token))
        assert r.status_code == 200

    def test_not_found(self, client, user_token):
        r = client.get("/api/v1/reminders/ghost-id",
                       headers=auth_headers(user_token))
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Update reminder
# ---------------------------------------------------------------------------

class TestUpdateReminder:
    def test_update_remind_time(self, client, reminder, user_token):
        r = client.put(
            f"/api/v1/reminders/{reminder['_id']}",
            json={"remind_time": "14:30"},
            headers=auth_headers(user_token),
        )
        assert r.status_code == 200
        assert r.json()["reminder"]["remind_time"] == "14:30"

    def test_toggle_is_active(self, client, reminder, user_token):
        r = client.put(
            f"/api/v1/reminders/{reminder['_id']}",
            json={"is_active": False},
            headers=auth_headers(user_token),
        )
        assert r.status_code == 200
        assert r.json()["reminder"]["is_active"] is False

    def test_update_invalid_time_rejected(self, client, reminder, user_token):
        r = client.put(
            f"/api/v1/reminders/{reminder['_id']}",
            json={"remind_time": "99:99"},
            headers=auth_headers(user_token),
        )
        assert r.status_code == 422

    def test_other_user_cannot_update(self, client, reminder, user2_token):
        r = client.put(
            f"/api/v1/reminders/{reminder['_id']}",
            json={"remind_time": "11:00"},
            headers=auth_headers(user2_token),
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Delete reminder
# ---------------------------------------------------------------------------

class TestDeleteReminder:
    def test_owner_can_delete(self, client, reminder, user_token):
        r = client.delete(f"/api/v1/reminders/{reminder['_id']}",
                          headers=auth_headers(user_token))
        assert r.status_code == 200
        # Đã xóa
        r2 = client.get(f"/api/v1/reminders/{reminder['_id']}",
                        headers=auth_headers(user_token))
        assert r2.status_code == 404

    def test_other_user_cannot_delete(self, client, reminder, user2_token):
        r = client.delete(f"/api/v1/reminders/{reminder['_id']}",
                          headers=auth_headers(user2_token))
        assert r.status_code == 403

    def test_delete_nonexistent_returns_404(self, client, user_token):
        r = client.delete("/api/v1/reminders/ghost",
                          headers=auth_headers(user_token))
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# List reminders by prescription
# ---------------------------------------------------------------------------

class TestRemindersByPrescription:
    def test_list_by_prescription(self, client, user_token, prescription, reminder):
        r = client.get(
            f"/api/v1/reminders/prescription/{prescription['_id']}",
            headers=auth_headers(user_token),
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_other_user_cannot_list(self, client, prescription,
                                    reminder, user2_token):
        r = client.get(
            f"/api/v1/reminders/prescription/{prescription['_id']}",
            headers=auth_headers(user2_token),
        )
        assert r.status_code == 403

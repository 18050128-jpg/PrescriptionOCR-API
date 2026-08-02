"""
test_prescription.py — luồng upload OCR, CRUD toa thuốc, phân quyền.
"""

import io
import pytest
from unittest.mock import patch

from app.test.conftest import (
    register_user, login_user, auth_headers,
    upload_prescription, FAKE_OCR_RESULT,
)


# ---------------------------------------------------------------------------
# Upload + OCR extraction
# ---------------------------------------------------------------------------

class TestUploadOCR:
    def test_upload_requires_auth(self, client):
        fake = io.BytesIO(b"data")
        r = client.post(
            "/api/v1/prescriptions/upload-ocr-extract",
            files={"file": ("test.jpg", fake, "image/jpeg")},
        )
        assert r.status_code == 401

    def test_upload_returns_prescription_document(self, client, user_token):
        presc = upload_prescription(client, user_token)
        assert "_id" in presc
        assert "created_at" in presc
        assert "medicines" in presc

    def test_upload_links_to_current_user(self, client, user_token):
        presc = upload_prescription(client, user_token)
        me = client.get("/api/v1/auth/me",
                        headers=auth_headers(user_token)).json()
        me_id = me.get("_id") or me.get("id", "")
        assert presc["user_id"] == me_id

    def test_upload_extracts_bhyt_fields(self, client, user_token):
        presc = upload_prescription(client, user_token)
        assert presc["prescription_type"] == "bhyt"
        assert presc["patient_name"] is not None
        assert len(presc["medicines"]) > 0

    def test_upload_invalid_extension_rejected(self, client, user_token):
        fake = io.BytesIO(b"data")
        r = client.post(
            "/api/v1/prescriptions/upload-ocr-extract",
            files={"file": ("test.pdf", fake, "application/pdf")},
            headers=auth_headers(user_token),
        )
        assert r.status_code == 400
        assert "jpg" in r.json()["detail"].lower() or "png" in r.json()["detail"].lower()

    def test_upload_png_accepted(self, client, user_token):
        fake = io.BytesIO(b"fake-png-data")
        r = client.post(
            "/api/v1/prescriptions/upload-ocr-extract",
            files={"file": ("test.png", fake, "image/png")},
            headers=auth_headers(user_token),
        )
        assert r.status_code == 201

    def test_ocr_failure_returns_500(self, client, user_token, mock_ocr):
        mock_ocr.predict.side_effect = RuntimeError("GPU error")
        fake = io.BytesIO(b"data")
        r = client.post(
            "/api/v1/prescriptions/upload-ocr-extract",
            files={"file": ("test.jpg", fake, "image/jpeg")},
            headers=auth_headers(user_token),
        )
        assert r.status_code == 500
        assert "OCR" in r.json()["detail"]


# ---------------------------------------------------------------------------
# List prescriptions
# ---------------------------------------------------------------------------

class TestListPrescriptions:
    def test_user_sees_only_own_prescriptions(self, client, user_token, user2_token):
        # user1 upload 2 toa
        upload_prescription(client, user_token)
        upload_prescription(client, user_token)
        # user2 upload 1 toa
        upload_prescription(client, user2_token)

        r = client.get("/api/v1/prescriptions/",
                       headers=auth_headers(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2

    def test_empty_list_for_new_user(self, client, user_token):
        r = client.get("/api/v1/prescriptions/",
                       headers=auth_headers(user_token))
        assert r.json()["total"] == 0

    def test_list_requires_auth(self, client):
        r = client.get("/api/v1/prescriptions/")
        assert r.status_code == 401

    def test_newest_first_order(self, client, user_token):
        import time
        p1 = upload_prescription(client, user_token)
        time.sleep(1)   # đảm bảo created_at khác nhau
        p2 = upload_prescription(client, user_token)
        r = client.get("/api/v1/prescriptions/",
                       headers=auth_headers(user_token))
        ids = [p["_id"] for p in r.json()["prescriptions"]]
        # p2 mới hơn → phải đứng đầu
        assert ids[0] == p2["_id"]


# ---------------------------------------------------------------------------
# Get single prescription
# ---------------------------------------------------------------------------

class TestGetPrescription:
    def test_owner_can_get_own(self, client, prescription, user_token):
        r = client.get(f"/api/v1/prescriptions/{prescription['_id']}",
                       headers=auth_headers(user_token))
        assert r.status_code == 200
        assert r.json()["_id"] == prescription["_id"]

    def test_other_user_cannot_get(self, client, prescription, user2_token):
        r = client.get(f"/api/v1/prescriptions/{prescription['_id']}",
                       headers=auth_headers(user2_token))
        assert r.status_code == 403

    def test_admin_can_get_any(self, client, prescription, admin_token):
        r = client.get(f"/api/v1/prescriptions/{prescription['_id']}",
                       headers=auth_headers(admin_token))
        assert r.status_code == 200

    def test_not_found_returns_404(self, client, user_token):
        r = client.get("/api/v1/prescriptions/nonexistent-id",
                       headers=auth_headers(user_token))
        assert r.status_code == 404

    def test_get_requires_auth(self, client, prescription):
        r = client.get(f"/api/v1/prescriptions/{prescription['_id']}")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Delete prescription
# ---------------------------------------------------------------------------

class TestDeletePrescription:
    def test_owner_can_delete(self, client, user_token):
        presc = upload_prescription(client, user_token)
        r = client.delete(f"/api/v1/prescriptions/{presc['_id']}",
                          headers=auth_headers(user_token))
        assert r.status_code == 200
        # Kiểm tra đã xóa thật
        r2 = client.get(f"/api/v1/prescriptions/{presc['_id']}",
                        headers=auth_headers(user_token))
        assert r2.status_code == 404

    def test_other_user_cannot_delete(self, client, prescription,
                                      user2_token, user_token):
        r = client.delete(f"/api/v1/prescriptions/{prescription['_id']}",
                          headers=auth_headers(user2_token))
        assert r.status_code == 403
        # Vẫn còn tồn tại
        r2 = client.get(f"/api/v1/prescriptions/{prescription['_id']}",
                        headers=auth_headers(user_token))
        assert r2.status_code == 200

    def test_admin_can_delete_any(self, client, prescription, admin_token):
        r = client.delete(f"/api/v1/prescriptions/{prescription['_id']}",
                          headers=auth_headers(admin_token))
        assert r.status_code == 200

    def test_delete_nonexistent_returns_404(self, client, user_token):
        r = client.delete("/api/v1/prescriptions/ghost-id",
                          headers=auth_headers(user_token))
        assert r.status_code == 404

    def test_delete_requires_auth(self, client, prescription):
        r = client.delete(f"/api/v1/prescriptions/{prescription['_id']}")
        assert r.status_code == 401

"""
conftest.py — fixtures dùng chung cho toàn bộ test suite.

Chiến lược isolation:
  - Mỗi test function nhận một thư mục JSON tạm riêng (tmp_path của pytest).
  - Monkey-patch DATA_DIR của json_store → không chạm file thật.
  - Mock hoàn toàn OCR (PaddleOCR) để test không cần GPU/model.
  - TestClient của FastAPI chạy trong process, không cần server thật.
"""

import io
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_collection(data_dir: Path, name: str, records: list[dict]) -> None:
    (data_dir / f"{name}.json").write_text(
        json.dumps({"records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_collection(data_dir: Path, name: str) -> list[dict]:
    p = data_dir / f"{name}.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("records", [])


# ---------------------------------------------------------------------------
# Core fixture: isolated JSON store per test
# ---------------------------------------------------------------------------

@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch):
    """
    Tạo thư mục tạm và patch DATA_DIR trong json_store.
    Mỗi test có store riêng, hoàn toàn cô lập.
    """
    import app.database.json_store as store
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    # Reset lock cache để không dùng lock của test trước
    monkeypatch.setattr(store, "_locks", {})
    return tmp_path


# ---------------------------------------------------------------------------
# Mock OCR — tránh load PaddleOCR thật
# ---------------------------------------------------------------------------

FAKE_OCR_RESULT = [
    {"text": "PHONG KHAM DA KHOA AN KHANG",   "confidence": 0.99},
    {"text": "TOA THUOC BHYT",                 "confidence": 0.98},
    {"text": "Ho va ten: NGUYEN VAN A",        "confidence": 0.97},
    {"text": "Chan doan: Viem hong cap",       "confidence": 0.96},
    {"text": "Ngay 01 / 01 / 2025",            "confidence": 0.95},
    {"text": "1 )  AMOXICILLIN 500mg",         "confidence": 0.94},
    {"text": "SL: 21 Vien",                    "confidence": 0.93},
    {"text": "Ghi chu Uong: Sang 1 Vien Chieu 1 Vien Toi 1 Vien", "confidence": 0.92},
    {"text": "BS. Tran Thi B",                 "confidence": 0.91},
]


@pytest.fixture(autouse=True)
def mock_ocr():
    """Patch toàn bộ OCR — áp dụng cho mọi test."""
    with patch("app.services.ocr_service._ocr_instance") as mock_inst:
        mock_inst.predict.return_value = [
            {
                "rec_texts":  [r["text"]  for r in FAKE_OCR_RESULT],
                "rec_scores": [r["confidence"] for r in FAKE_OCR_RESULT],
            }
        ]
        yield mock_inst


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(data_dir):
    """
    TestClient đã được gắn với JSON store tạm.
    Cần import app SAU KHI data_dir đã patch DATA_DIR.
    """
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def register_user(client, username="testuser", password="pass123",
                  email=None, full_name=None) -> dict:
    email = email or f"{username}@test.com"
    payload = {"username": username, "password": password, "email": email}
    if full_name:
        payload["full_name"] = full_name
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def login_user(client, username="testuser", password="pass123") -> str:
    """Trả về access_token string."""
    r = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Preset fixtures: admin + regular user đã đăng ký sẵn
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_token(client) -> str:
    """User đầu tiên → admin."""
    data = register_user(client, username="admin", email="admin@test.com")
    return data["access_token"]


@pytest.fixture()
def user_token(client, admin_token) -> str:
    """User thứ hai → role=user."""
    data = register_user(client, username="user1", email="user1@test.com")
    return data["access_token"]


@pytest.fixture()
def user2_token(client, admin_token, user_token) -> str:
    """User thứ ba — dùng để test cross-user isolation."""
    data = register_user(client, username="user2", email="user2@test.com")
    return data["access_token"]


# ---------------------------------------------------------------------------
# Prescription fixture
# ---------------------------------------------------------------------------

def upload_prescription(client, token: str) -> dict:
    """Upload ảnh giả → nhận prescription document."""
    fake_image = io.BytesIO(b"fake-image-data")
    fake_image.name = "test.jpg"
    r = client.post(
        "/api/v1/prescriptions/upload-ocr-extract",
        files={"file": ("test.jpg", fake_image, "image/jpeg")},
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["prescription"]


@pytest.fixture()
def prescription(client, user_token) -> dict:
    """Một prescription thuộc user1."""
    return upload_prescription(client, user_token)


# ---------------------------------------------------------------------------
# Reminder fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def reminder(client, user_token, prescription) -> dict:
    """Một reminder thuộc user1 → prescription trên."""
    r = client.post(
        "/api/v1/reminders/",
        json={
            "prescription_id": prescription["_id"],
            "medicine_name":   "AMOXICILLIN",
            "remind_time":     "08:00",
            "days_of_week":    [],
            "note":            "Uống sau ăn sáng",
        },
        headers=auth_headers(user_token),
    )
    assert r.status_code == 201, r.text
    return r.json()["reminder"]

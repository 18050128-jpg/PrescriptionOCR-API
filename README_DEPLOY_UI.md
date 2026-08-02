# Deploy nhanh cho frontend demo

Tài liệu này hướng dẫn bạn chạy backend API của dự án để frontend có thể test giao diện ngay.

## 1. Môi trường cần có

- Python 3.11+
- phụ thuộc trong `requirements.txt` đã được cài

## 2. Chạy backend

Từ thư mục gốc của repo:

```powershell
cd PrescriptionOCR
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> Với mục đích demo UI, nên bật mock OCR để không phụ thuộc vào model PaddleOCR thực tế:

```powershell
set MOCK_OCR=1
set CORS_ALLOW_ALL=1
```

Khởi động server:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 3. Truy cập API

Sau khi server chạy, frontend có thể dùng các URL sau:

- Swagger docs: `http://127.0.0.1:8000/docs`
- Root redirect: `http://127.0.0.1:8000/`

## 4. Các endpoint demo quan trọng

### Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### Prescription
- `POST /api/v1/prescriptions/upload-ocr-extract`
- `GET /api/v1/prescriptions/`

### Reminder
- `POST /api/v1/reminders/`
- `GET /api/v1/reminders/`

### Notification
- `GET /api/v1/notifications/`

## 5. Gợi ý cho frontend

- Dùng `Authorization: Bearer <token>` trong header khi gọi các endpoint cần login.
- Với demo UI, có thể để `CORS_ALLOW_ALL=1` để frontend chạy ở domain khác.
- Nếu dùng mock OCR, hình ảnh upload sẽ trả về dữ liệu mẫu ổn định cho test UI.

## 6. Lưu ý

- Đây là hướng dẫn cho demo UI, không phải production-ready.
- Nếu deploy thật, nên thay đổi secret JWT, khóa CORS, và chuyển JSON store sang database chuyên dụng.

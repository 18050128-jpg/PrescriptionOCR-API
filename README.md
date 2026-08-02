# Prescription OCR API

Backend FastAPI dùng để nhận dạng và trích xuất thông tin từ toa thuốc ảnh, hỗ trợ đăng ký/đăng nhập, quản lý toa thuốc, lịch nhắc uống thuốc và thông báo nhắc nhở.

## 1. Mục tiêu dự án

Dự án này phục vụ các chức năng chính sau:

- Upload ảnh toa thuốc
- Gọi OCR để trích xuất văn bản từ hình ảnh
- Xử lý và chuẩn hóa dữ liệu toa thuốc thành cấu trúc JSON
- Lưu trữ prescription, user, reminder, notification trong store JSON
- Hỗ trợ xác thực JWT và phân quyền theo role
- Hỗ trợ nhắc uống thuốc theo lịch bằng scheduler nền

## 2. Công nghệ sử dụng

- Python 3.11+
- FastAPI
- Uvicorn
- PaddleOCR
- JWT (`python-jose`)
- bcrypt
- APScheduler
- pytest

## 3. Cấu trúc thư mục

```text
PrescriptionOCR/
├── app/
│   ├── api/               # Router FastAPI
│   ├── core/              # Security / auth dependency
│   ├── database/          # JSON store và file dữ liệu
│   ├── models/            # Schema / entity tương ứng
│   ├── repositories/      # CRUD qua JSON store
│   ├── schemas/           # Pydantic schema
│   ├── services/          # OCR, extraction, auth, scheduler
│   ├── test/              # Test suite
│   └── uploads/           # Hình ảnh upload
├── requirements.txt       # Dependency
├── pytest.ini             # Cấu hình pytest
└── run_all_tests.py       # Chạy tất cả test và ghi file kết quả
```

## 4. Yêu cầu môi trường

Trước khi chạy dự án, hãy đảm bảo:

- Python 3.11 hoặc mới hơn
- virtual environment đã được tạo và kích hoạt
- `pip` đã sẵn sàng cài package

## 5. Cài đặt

### 5.1 Tạo môi trường ảo

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 5.2 Cài dependency

```bash
pip install -r requirements.txt
```

## 6. Cấu hình môi trường

Một số thông tin cấu hình được lấy từ biến môi trường:

- `SECRET_KEY`: khóa bí mật để ký JWT. Nếu không set, hệ thống dùng default tạm thời.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: thời hạn access token (mặc định 1440 phút).
- `MOCK_OCR=1`: bật mode OCR giả để test/runtime không cần tải PaddleOCR model.
- `PADDLE_PDX_MODEL_HOME`: đường dẫn cache model OCR. Nếu không set, dự án sẽ dùng folder local `.paddlex_models` trong repo để cache lại model.

Ví dụ:

```bash
set SECRET_KEY=your-secret-key
set ACCESS_TOKEN_EXPIRE_MINUTES=1440
set MOCK_OCR=1
set PADDLE_PDX_MODEL_HOME=.paddlex_models
```

> Lưu ý quan trọng cho môi trường chạy OCR thật:
> - hệ thống cần model OCR có sẵn trong cache hoặc internet để download lần đầu
> - nếu đang chạy test hoặc CI offline, nên đặt `MOCK_OCR=1`
> - nếu đang chạy production/real OCR, hãy đảm bảo `PADDLE_PDX_MODEL_HOME` trỏ đến đường dẫn cache ổn định và không bị xóa sau mỗi lần chạy

## 7. Chạy ứng dụng

### 7.1 Khởi động server dev

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7.2 Kiểm tra ứng dụng

Mở trình duyệt hoặc công cụ API test:

```text
http://localhost:8000/docs
```

Swagger UI sẽ hiển thị toàn bộ API docs cho bạn test trực tiếp.

## 8. API overview

### 8.1 Auth

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/auth/register` | Đăng ký tài khoản mới |
| POST | `/api/v1/auth/login` | Đăng nhập, nhận JWT |
| GET | `/api/v1/auth/me` | Lấy thông tin user hiện tại |
| PUT | `/api/v1/auth/me` | Cập nhật profile |

### 8.2 Prescription

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/prescriptions/upload-ocr-extract` | Upload ảnh, OCR, extract, lưu prescription |
| GET | `/api/v1/prescriptions/` | Lấy danh sách prescription của user hiện tại |
| GET | `/api/v1/prescriptions/{prescription_id}` | Xem chi tiết một prescription |
| DELETE | `/api/v1/prescriptions/{prescription_id}` | Xóa prescription |

### 8.3 Reminder

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/reminders/` | Tạo reminder |
| GET | `/api/v1/reminders/` | Xem reminders của user hiện tại |
| GET | `/api/v1/reminders/{reminder_id}` | Xem chi tiết một reminder |
| PUT | `/api/v1/reminders/{reminder_id}` | Cập nhật reminder |
| DELETE | `/api/v1/reminders/{reminder_id}` | Xóa reminder |
| GET | `/api/v1/reminders/prescription/{prescription_id}` | Xem reminders theo prescription |

### 8.4 Notification

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/notifications/` | Lấy notification của user hiện tại |
| PUT | `/api/v1/notifications/{notification_id}/read` | Đánh dấu 1 notification đã đọc |
| PUT | `/api/v1/notifications/read-all` | Đánh dấu tất cả notification đã đọc |
| DELETE | `/api/v1/notifications/{notification_id}` | Xóa một notification |

### 8.5 Admin

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/admin/users` | Lấy danh sách users |
| GET | `/api/v1/admin/users/{user_id}` | Xem chi tiết user |
| PUT | `/api/v1/admin/users/{user_id}/role` | Thay đổi role |
| PUT | `/api/v1/admin/users/{user_id}/toggle-active` | Bật/tắt tài khoản |
| DELETE | `/api/v1/admin/users/{user_id}` | Xóa user và dữ liệu liên quan |
| GET | `/api/v1/admin/prescriptions` | Xem tất cả prescription |
| GET | `/api/v1/admin/stats` | Xem thống kê hệ thống |

## 9. Auth flow

- User đăng ký hoặc đăng nhập
- Server trả về JWT access token
- Client gửi token trong header `Authorization: Bearer <token>`
- FastAPI dependency kiểm tra token và xác định user hiện tại

Ví dụ request header:

```http
Authorization: Bearer <access_token>
```

## 10. Dữ liệu lưu trữ

Dữ liệu không dùng database SQL. Thay vào đó, dự án lưu kết quả vào các file JSON trong thư mục:

- `app/database/users.json`
- `app/database/prescriptions.json`
- `app/database/reminders.json`
- `app/database/notifications.json`

Đây là store file-based, phù hợp cho demo / MVP.

## 11. Scheduler nhắc uống thuốc

Khi ứng dụng khởi động, scheduler nền được bật để kiểm tra các reminder đang active. Nếu thời gian `remind_time` khớp với thời điểm hiện tại, hệ thống tạo notification mới.

## 12. Chạy test

Trong môi trường test/CI, nên đặt biến môi trường:

```bash
set MOCK_OCR=1
```

Điều này giúp luồng OCR không phụ thuộc vào việc tải model PaddleOCR từ mạng.

### Chạy tất cả test

```bash
python -m pytest -v
```

### Chạy bộ test của từng module

```bash
python -m pytest app/test/test_auth.py
python -m pytest app/test/test_prescription.py
python -m pytest app/test/test_reminder.py
python -m pytest app/test/test_notification.py
python -m pytest app/test/test_admin.py
```

### Chạy file wrapper tổng hợp

```bash
python run_all_tests.py
```

Kết quả test sẽ được ghi ra file `test_result.txt`.

## 13. Lưu ý triển khai

- Không nên dùng `allow_origins=["*"]` trong production nếu có thể tránh.
- Không nên để `SECRET_KEY` mặc định trong môi trường thực.
- Nên chuyển lưu trữ từ JSON file sang database chính thức nếu cần mở rộng hệ thống lớn hơn.
- Nên quản lý uploads và OCR output rõ ràng để tránh ảnh và dữ liệu không kiểm soát.

## 14. Tóm tắt

Dự án là một API FastAPI để:

- nhận diện toa thuốc từ hình ảnh
- trích xuất thông tin bên trong toa
- lưu và thao tác với dữ liệu người dùng
- nhắc lịch uống thuốc thông qua notification + scheduler

Nó phù hợp cho mô hình MVP / demo, và có thể nâng cấp thành sản phẩm đầy đủ hơn khi có thêm database chuyên dụng, độ chính xác OCR cao hơn và pipeline bảo mật production-ready.
"# PrescriptionOCR-API" 

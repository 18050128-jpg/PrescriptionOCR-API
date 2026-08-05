# Prescription OCR API

Backend FastAPI xử lý upload ảnh toa thuốc, trích xuất OCR, quản lý user, prescription, reminder và notification.

## Mục tiêu

- Upload ảnh toa thuốc và nhận dạng OCR
- Trích xuất thông tin thuốc sang cấu trúc JSON
- Quản lý đơn thuốc, nhắc uống thuốc và thông báo
- Xác thực JWT và phân quyền user/admin
- Lưu dữ liệu bằng JSON file store

## Khởi động

```bash
cd PrescriptionOCR
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Kiểm tra API

Truy cập Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Biến môi trường

Sử dụng file `.env` hoặc thiết lập biến môi trường:

- `SECRET_KEY` - khóa bí mật JWT
- `ACCESS_TOKEN_EXPIRE_MINUTES` - thời hạn token
- `MOCK_OCR=1` - bật OCR giả cho test/CI
- `PADDLE_PDX_MODEL_HOME` - đường dẫn cache model PaddleOCR
- `CORS_ALLOW_ALL=1` - cho phép CORS mọi nguồn
- `CORS_ALLOWED_ORIGINS` - danh sách domain được phép truy cập

Ví dụ:

```bash
set SECRET_KEY=your-secret-key
set ACCESS_TOKEN_EXPIRE_MINUTES=1440
set MOCK_OCR=1
set PADDLE_PDX_MODEL_HOME=.paddlex_models
```

## Cấu trúc chính

```text
PrescriptionOCR/
├── app/
│   ├── api/               # FastAPI routes
│   ├── core/              # Xác thực và security
│   ├── database/          # JSON store và dữ liệu
│   ├── models/            # Entity models
│   ├── repositories/      # CRUD với JSON store
│   ├── schemas/           # Pydantic schema
│   ├── services/          # OCR, auth, scheduler, logic
│   ├── test/              # Unit tests
│   └── uploads/           # File upload
├── requirements.txt       # Dependencies
├── pytest.ini             # Cấu hình pytest
└── run_all_tests.py       # Chạy tất cả test
```

## Data storage

Dữ liệu được lưu trong các file JSON:

- `app/database/users.json`
- `app/database/prescriptions.json`
- `app/database/reminders.json`
- `app/database/notifications.json`

> Lưu ý: giải pháp file-based phù hợp cho demo/MVP, không khuyến nghị dùng cho production quy mô lớn.

## API chính

- `POST /api/v1/auth/register` - đăng ký
- `POST /api/v1/auth/login` - đăng nhập, nhận JWT
- `POST /api/v1/prescriptions/upload-ocr-extract` - upload ảnh, OCR, lưu prescription
- `GET /api/v1/prescriptions/` - lấy list prescription
- `GET /api/v1/prescriptions/{prescription_id}` - xem chi tiết
- `POST /api/v1/reminders/` - tạo reminder
- `GET /api/v1/reminders/` - lấy reminder của user
- `GET /api/v1/notifications/` - lấy notification
- `GET /api/v1/admin/users` - quản lý user (admin)

## Testing

Khi chạy test nên bật OCR giả:

```bash
set MOCK_OCR=1
python -m pytest
```

## Lưu ý

- Khi chạy OCR thật, cần có model PaddleOCR cache sẵn hoặc internet để tải lần đầu.
- Nếu muốn chạy frontend và backend cùng lúc, khởi động backend trước và cấu hình `VITE_API_URL` trong frontend.


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

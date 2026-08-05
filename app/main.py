import os
from contextlib import asynccontextmanager
from pathlib import Path


def _load_env_file() -> None:
    """Nạp biến môi trường từ file .env ở thư mục gốc repo nếu tồn tại."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env_file()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.prescription import router as prescription_router
from app.api.auth import router as auth_router
from app.api.reminder import router as reminder_router
from app.api.notification import router as notification_router
from app.api.admin import router as admin_router
from app.api.medicine import router as medicine_router
from app.services.reminder_scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động scheduler nhắc uống thuốc khi app start
    start_scheduler()
    yield
    # Dừng scheduler khi app shutdown
    stop_scheduler()


app = FastAPI(
    title="Prescription OCR API",
    version="2.0.0",
    description=(
        "API nhận dạng và trích xuất thông tin đơn thuốc từ ảnh. "
        "Hỗ trợ đăng nhập, phân quyền admin/user và nhắc lịch uống thuốc."
    ),
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs", status_code=307)


# CORS — thuận tiện cho demo UI nhưng vẫn hỗ trợ cấu hình bằng biến môi trường.
cors_allow_all = os.getenv("CORS_ALLOW_ALL", "0").strip().lower() in {"1", "true", "yes", "on"}
cors_origins = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
)
allowed_origins = [
    origin.strip()
    for origin in cors_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if cors_allow_all else ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(prescription_router)
app.include_router(reminder_router)
app.include_router(notification_router)
app.include_router(admin_router)
app.include_router(medicine_router)

"""
Admin API — chỉ dành cho role = admin.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.repositories import user_repository, prescription_repository, reminder_repository
from app.database import json_store
from app.core.security import require_admin
from app.services.auth_service import hash_password

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

NOTIF_COLLECTION = "notifications"


def _options_response() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={"status": "ok"},
        headers={
            "Allow": "POST, OPTIONS",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
        },
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_all_users(_: dict = Depends(require_admin)):
    """Lấy danh sách tất cả users."""
    users = user_repository.get_all()
    # Ẩn hashed_password trước khi trả về
    safe = [{k: v for k, v in u.items() if k != "hashed_password"} for u in users]
    return {"total": len(safe), "users": safe}


@router.get("/users/{user_id}")
async def get_user(user_id: str, _: dict = Depends(require_admin)):
    """Lấy thông tin một user."""
    user = user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    safe = {k: v for k, v in user.items() if k != "hashed_password"}
    return safe


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: dict,
    current_admin: dict = Depends(require_admin),
):
    """
    Thay đổi role của user (admin / user).
    Admin không thể tự hạ quyền chính mình.
    """
    new_role = body.get("role")
    if new_role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role phải là 'admin' hoặc 'user'")
    if user_id == current_admin["_id"] and new_role != "admin":
        raise HTTPException(status_code=400, detail="Không thể tự hạ quyền admin của chính mình")

    user = user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    updated = user_repository.update(user_id, {"role": new_role})
    safe = {k: v for k, v in updated.items() if k != "hashed_password"}
    return {"status": "success", "user": safe}


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    current_admin: dict = Depends(require_admin),
):
    """Bật/tắt tài khoản user."""
    if user_id == current_admin["_id"]:
        raise HTTPException(status_code=400, detail="Không thể tự vô hiệu hoá tài khoản của mình")

    user = user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    new_status = not user.get("is_active", True)
    updated = user_repository.update(user_id, {"is_active": new_status})
    safe = {k: v for k, v in updated.items() if k != "hashed_password"}
    return {"status": "success", "user": safe}


@router.delete("/users/{user_id}", status_code=200)
async def delete_user(user_id: str, current_admin: dict = Depends(require_admin)):
    """Xóa user (và tất cả prescriptions + reminders liên quan)."""
    if user_id == current_admin["_id"]:
        raise HTTPException(status_code=400, detail="Không thể xóa chính mình")

    user = user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    # Xóa các dữ liệu liên quan
    for presc in prescription_repository.get_by_user(user_id):
        prescription_repository.delete(presc["_id"])
    for rem in reminder_repository.get_by_user(user_id):
        reminder_repository.delete(rem["_id"])
    for notif in json_store.find_by_field(NOTIF_COLLECTION, "user_id", user_id):
        json_store.delete_by_id(NOTIF_COLLECTION, notif["_id"])

    user_repository.delete(user_id)
    return {"status": "success", "message": f"Đã xóa user {user_id} và toàn bộ dữ liệu liên quan"}


@router.options("/users/create-admin")
async def options_create_admin_v1():
    return _options_response()


@router.options("/create-admin")
async def options_create_admin_v2():
    return _options_response()


@router.post("/users/create-admin")
async def create_admin_account(body: dict, _: dict = Depends(require_admin)):
    """Tạo tài khoản admin mới."""
    username = body.get("username")
    email = body.get("email")
    password = body.get("password")
    full_name = body.get("full_name")

    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="Cần username, email và password")
    if user_repository.get_by_username(username):
        raise HTTPException(status_code=400, detail="Username đã tồn tại")
    if user_repository.get_by_email(email):
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    hashed = hash_password(password)
    doc = user_repository.create(
        username=username,
        email=email,
        hashed_password=hashed,
        full_name=full_name or username,
        role="admin",
    )
    safe = {k: v for k, v in doc.items() if k != "hashed_password"}
    return {"status": "success", "user": safe}


@router.post("/create-admin")
async def create_admin_account_v2(body: dict, _: dict = Depends(require_admin)):
    """Đường dẫn thay thế để UI gọi dễ dàng hơn."""
    return await create_admin_account(body, _)


@router.put("/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, body: dict, _: dict = Depends(require_admin)):
    """Đặt lại mật khẩu cho user/admin."""
    new_password = body.get("password")
    if not new_password:
        raise HTTPException(status_code=400, detail="Cần cung cấp password mới")

    user = user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    hashed = hash_password(new_password)
    updated = user_repository.update(user_id, {"hashed_password": hashed})
    safe = {k: v for k, v in updated.items() if k != "hashed_password"}
    return {"status": "success", "message": "Đã reset mật khẩu", "user": safe}


# ---------------------------------------------------------------------------
# Prescriptions (admin view)
# ---------------------------------------------------------------------------

@router.get("/prescriptions")
async def list_all_prescriptions(_: dict = Depends(require_admin)):
    """Lấy toàn bộ prescriptions của tất cả users."""
    records = prescription_repository.get_all()
    return {"total": len(records), "prescriptions": records}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def stats(_: dict = Depends(require_admin)):
    """Thống kê tổng quan hệ thống."""
    return {
        "total_users":         user_repository.total(),
        "total_prescriptions": prescription_repository.total(),
        "total_reminders":     json_store.count("reminders"),
        "total_notifications": json_store.count(NOTIF_COLLECTION),
    }

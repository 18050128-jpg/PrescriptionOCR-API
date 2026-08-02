"""
Reminder API — CRUD lịch nhắc uống thuốc cho user hiện tại.
"""

from fastapi import APIRouter, HTTPException, Depends

from app.schemas.reminder import ReminderCreate, ReminderUpdate
from app.repositories import reminder_repository, prescription_repository
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/reminders", tags=["Reminder"])


def _check_owner(reminder: dict, current_user: dict) -> None:
    """Kiểm tra reminder có thuộc về user không (admin được phép xem tất cả)."""
    if current_user.get("role") != "admin" and reminder.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Không có quyền thao tác reminder này")


@router.post("/", status_code=201)
async def create_reminder(
    body: ReminderCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Tạo lịch nhắc uống thuốc.
    prescription_id phải thuộc về user đang đăng nhập.
    """
    # Kiểm tra prescription tồn tại và thuộc user
    presc = prescription_repository.get_by_id(body.prescription_id)
    if presc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy prescription")
    if current_user.get("role") != "admin" and presc.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Prescription không thuộc về bạn")

    doc = reminder_repository.create(
        user_id=current_user["_id"],
        prescription_id=body.prescription_id,
        medicine_name=body.medicine_name,
        remind_time=body.remind_time,
        days_of_week=body.days_of_week,
        note=body.note,
    )
    return {"status": "success", "reminder": doc}


@router.get("/")
async def list_my_reminders(current_user: dict = Depends(get_current_user)):
    """Lấy tất cả reminders của user đang đăng nhập."""
    records = reminder_repository.get_by_user(current_user["_id"])
    return {"total": len(records), "reminders": records}


@router.get("/{reminder_id}")
async def get_reminder(
    reminder_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Lấy chi tiết một reminder."""
    doc = reminder_repository.get_by_id(reminder_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy reminder")
    _check_owner(doc, current_user)
    return doc


@router.put("/{reminder_id}")
async def update_reminder(
    reminder_id: str,
    body: ReminderUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Cập nhật reminder (giờ nhắc, ngày trong tuần, ghi chú, bật/tắt)."""
    doc = reminder_repository.get_by_id(reminder_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy reminder")
    _check_owner(doc, current_user)

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = reminder_repository.update(reminder_id, updates)
    return {"status": "success", "reminder": updated}


@router.delete("/{reminder_id}", status_code=200)
async def delete_reminder(
    reminder_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Xóa reminder."""
    doc = reminder_repository.get_by_id(reminder_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy reminder")
    _check_owner(doc, current_user)

    reminder_repository.delete(reminder_id)
    return {"status": "success", "message": f"Đã xóa reminder {reminder_id}"}


@router.get("/prescription/{prescription_id}")
async def list_reminders_by_prescription(
    prescription_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Lấy tất cả reminders theo toa thuốc."""
    presc = prescription_repository.get_by_id(prescription_id)
    if presc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy prescription")
    if current_user.get("role") != "admin" and presc.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Không có quyền")

    records = reminder_repository.get_by_prescription(prescription_id)
    return {"total": len(records), "reminders": records}

import re

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Optional

from app.services.file_service import validate_and_save
from app.services.prescription_service import process_and_save
from app.repositories import prescription_repository
from app.database import json_store
from app.core.security import get_current_user, require_admin

router = APIRouter(
    prefix="/api/v1/prescriptions",
    tags=["Prescription"]
)


@router.post("/upload-ocr-extract", status_code=201)
async def upload_ocr_extract(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload ảnh đơn thuốc → OCR → extract → lưu JSON store.
    Toa thuốc được liên kết với user đang đăng nhập.
    Trả về prescription document đầy đủ (bao gồm _id).
    """
    filename, filepath = validate_and_save(file)
    document = process_and_save(filename, filepath, user_id=current_user["_id"])
    return {
        "status": "success",
        "prescription": document,
    }


@router.get("/")
async def list_my_prescriptions(
    current_user: dict = Depends(get_current_user),
):
    """
    Lấy danh sách prescriptions của user đang đăng nhập, mới nhất lên đầu.
    """
    records = prescription_repository.get_by_user(current_user["_id"])
    return {
        "total": len(records),
        "prescriptions": records,
    }


def _parse_quantity(quantity: str) -> tuple[int, str] | None:
    if not quantity:
        return None
    match = re.match(r"^\s*([0-9]+)(?:[.,]([0-9]+))?\s*(.*)$", quantity)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(3).strip()
    return value, unit


def _decrease_quantity(quantity: str, amount: int = 1) -> str:
    parsed = _parse_quantity(quantity)
    if parsed is None:
        return quantity
    value, unit = parsed
    new_value = max(value - amount, 0)
    return f"{new_value} {unit}".strip() if unit else str(new_value)


@router.get("/{prescription_id}")
async def get_prescription(
    prescription_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Lấy chi tiết một prescription theo _id.
    User chỉ xem được prescription của mình; admin xem được tất cả.
    """
    doc = prescription_repository.get_by_id(prescription_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy prescription")

    if current_user.get("role") != "admin" and doc.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Không có quyền xem prescription này")

    return doc


@router.put("/{prescription_id}/medicines/{medicine_index}/use", status_code=200)
async def use_medicine(
    prescription_id: str,
    medicine_index: int,
    current_user: dict = Depends(get_current_user),
):
    """Giảm remaining của một thuốc trong đơn thuốc."""
    doc = prescription_repository.get_by_id(prescription_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy prescription")

    if current_user.get("role") != "admin" and doc.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Không có quyền cập nhật prescription này")

    medicines = doc.get("medicines", [])
    if medicine_index < 0 or medicine_index >= len(medicines):
        raise HTTPException(status_code=404, detail="Không tìm thấy thuốc")

    med = medicines[medicine_index]
    med["remaining"] = _decrease_quantity(med.get("remaining") or med.get("quantity") or "")

    updated = json_store.update_by_id("prescriptions", prescription_id, {"medicines": medicines})
    if updated is None:
        raise HTTPException(status_code=500, detail="Cập nhật failed.")

    return {"status": "success", "prescription": updated}


@router.delete("/{prescription_id}", status_code=200)
async def delete_prescription(
    prescription_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Xóa một prescription theo _id.
    User chỉ xóa được prescription của mình; admin xóa được tất cả.
    """
    doc = prescription_repository.get_by_id(prescription_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy prescription")

    if current_user.get("role") != "admin" and doc.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Không có quyền xóa prescription này")

    prescription_repository.delete(prescription_id)
    return {"status": "success", "message": f"Đã xóa prescription {prescription_id}"}

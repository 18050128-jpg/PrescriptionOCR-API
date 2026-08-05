from fastapi import APIRouter, Depends
from typing import Optional

from app.core.security import get_current_user
from app.repositories import medicine_repository
from fastapi import UploadFile, File
import csv
from io import StringIO

router = APIRouter(
    prefix="/api/v1/medicines",
    tags=["Medicines"],
)


@router.get("/")
def list_medicines(current_user: dict = Depends(get_current_user)):
    """Trả về danh sách medicines trong kho (dành cho người đã auth)."""
    records = medicine_repository.get_all() if hasattr(medicine_repository, "get_all") else []
    # Fallback: nếu repository chưa có get_all(), đọc toàn bộ collection
    if not records:
        from app.database import json_store
        records = json_store.find_all("medicines")
    return {"total": len(records), "medicines": records}


@router.get("/{medicine_id}")
def get_medicine(medicine_id: str, current_user: dict = Depends(get_current_user)):
    from app.database import json_store
    rec = json_store.find_by_id("medicines", medicine_id)
    if not rec:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Medicine not found")
    return rec


@router.post("/")
def create_medicine(payload: dict, current_user: dict = Depends(get_current_user)):
    """Tạo medicine mới (admin hoặc user auth)."""
    # minimal validation
    name = payload.get("name")
    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Missing name")
    doc = medicine_repository.create(payload)
    return doc


@router.post("/upload")
def upload_medicines(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Import medicines từ file CSV. Trường header: name, dosage, quantity, unit
    quantity có thể là '2 vỉ x 10 viên' hoặc '20 viên'."""
    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(StringIO(content))
    created = []
    errors = []
    for i, row in enumerate(reader):
        try:
            # Normalize keys
            item = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            # try upsert (will parse quantity)
            medicine_repository.upsert_from_prescription_item({
                "name": item.get("name", ""),
                "dosage": item.get("dosage", ""),
                "quantity": item.get("quantity", "") or f"{item.get('quantity_number','')}",
            })
            created.append(item.get("name", ""))
        except Exception as e:
            errors.append({"row": i + 1, "error": str(e)})

    return {"created": created, "errors": errors}


@router.get("/search")
def search_medicine(name: Optional[str] = None, dosage: Optional[str] = None, unit: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Missing name")
    found = medicine_repository.find_by_key(name, dosage or "", unit or "")
    if not found:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Medicine not found")
    return found


@router.put("/{medicine_id}")
def update_medicine(medicine_id: str, payload: dict, current_user: dict = Depends(get_current_user)):
    from app.database import json_store
    rec = json_store.find_by_id("medicines", medicine_id)
    if not rec:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Medicine not found")
    updated = json_store.update_by_id("medicines", medicine_id, payload)
    return updated


@router.delete("/{medicine_id}")
def delete_medicine(medicine_id: str, current_user: dict = Depends(get_current_user)):
    from app.database import json_store
    deleted = json_store.delete_by_id("medicines", medicine_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Medicine not found")
    return {"status": "success", "message": f"Deleted medicine {medicine_id}"}

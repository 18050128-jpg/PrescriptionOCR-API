"""
Repository layer — tất cả CRUD cho Prescription đi qua đây.
Không có code nào ngoài lớp này được phép gọi json_store trực tiếp.
"""

import uuid
from datetime import datetime

from app.database import json_store

COLLECTION = "prescriptions"


def create(extracted: dict, filename: str, image_path: str,
           user_id: str | None = None) -> dict:
    """
    Tạo document mới từ kết quả extraction + metadata file.

    Args:
        extracted:   Dict trả về từ extract_prescription()
        filename:    Tên file ảnh đã lưu
        image_path:  Đường dẫn file ảnh trên disk
        user_id:     ID của user sở hữu prescription (None = không xác thực)

    Returns:
        Document đã được lưu (bao gồm _id, created_at)
    """
    document = {
        "_id":        str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "user_id":    user_id,
        "filename":   filename,
        "image_path": image_path,
        **extracted,
    }
    return json_store.insert(COLLECTION, document)


def get_all() -> list[dict]:
    """Lấy toàn bộ prescriptions, mới nhất lên đầu."""
    records = json_store.find_all(COLLECTION)
    # Sắp xếp theo created_at giảm dần
    return sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)


def get_by_user(user_id: str) -> list[dict]:
    """Lấy tất cả prescriptions của một user, mới nhất lên đầu."""
    records = json_store.find_by_field(COLLECTION, "user_id", user_id)
    return sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)


def get_by_id(prescription_id: str) -> dict | None:
    """Lấy một prescription theo _id. None nếu không tồn tại."""
    return json_store.find_by_id(COLLECTION, prescription_id)


def delete(prescription_id: str) -> bool:
    """
    Xóa prescription theo _id và xóa file ảnh liên quan trên disk.

    Returns:
        True nếu xóa thành công, False nếu không tìm thấy.
    """
    import os

    doc = json_store.find_by_id(COLLECTION, prescription_id)
    if doc is None:
        return False

    deleted = json_store.delete_by_id(COLLECTION, prescription_id)

    if deleted:
        image_path = doc.get("image_path", "")
        if image_path and os.path.isfile(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass  # file đã bị xóa hoặc không có quyền — bỏ qua

    return deleted


def total() -> int:
    """Trả về tổng số prescriptions đang lưu."""
    return json_store.count(COLLECTION)

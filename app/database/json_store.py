"""
JSON File Store — lớp lưu trữ dữ liệu đơn giản dùng file JSON.

Mỗi "collection" là một file JSON riêng biệt.
Cấu trúc file:
{
    "records": [
        { "_id": "<uuid>", ... },
        ...
    ]
}
"""

import json
import os
import threading
from pathlib import Path
from typing import Any

DATA_DIR = Path("app/database")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Lock theo từng collection để thread-safe
_locks: dict[str, threading.Lock] = {}
_locks_meta = threading.Lock()


def _get_lock(collection: str) -> threading.Lock:
    with _locks_meta:
        if collection not in _locks:
            _locks[collection] = threading.Lock()
        return _locks[collection]


def _collection_path(collection: str) -> Path:
    return DATA_DIR / f"{collection}.json"


def _load(collection: str) -> list[dict]:
    path = _collection_path(collection)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("records", [])


def _save(collection: str, records: list[dict]) -> None:
    path = _collection_path(collection)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"records": records}, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def insert(collection: str, document: dict) -> dict:
    """Thêm document vào collection. Trả về document đã được lưu."""
    lock = _get_lock(collection)
    with lock:
        records = _load(collection)
        records.append(document)
        _save(collection, records)
    return document


def find_all(collection: str) -> list[dict]:
    """Lấy toàn bộ documents trong collection."""
    lock = _get_lock(collection)
    with lock:
        return _load(collection)


def find_by_id(collection: str, doc_id: str) -> dict | None:
    """Tìm document theo _id. Trả về None nếu không tìm thấy."""
    lock = _get_lock(collection)
    with lock:
        records = _load(collection)
    return next((r for r in records if r.get("_id") == doc_id), None)


def update_by_id(collection: str, doc_id: str, updates: dict) -> dict | None:
    """Cập nhật document theo _id. Trả về document sau khi cập nhật."""
    lock = _get_lock(collection)
    with lock:
        records = _load(collection)
        for i, record in enumerate(records):
            if record.get("_id") == doc_id:
                records[i] = {**record, **updates}
                _save(collection, records)
                return records[i]
    return None


def delete_by_id(collection: str, doc_id: str) -> bool:
    """Xóa document theo _id. Trả về True nếu xóa thành công."""
    lock = _get_lock(collection)
    with lock:
        records = _load(collection)
        new_records = [r for r in records if r.get("_id") != doc_id]
        if len(new_records) == len(records):
            return False
        _save(collection, new_records)
    return True


def count(collection: str) -> int:
    """Đếm số documents trong collection."""
    lock = _get_lock(collection)
    with lock:
        return len(_load(collection))


def find_by_field(collection: str, field: str, value: Any) -> list[dict]:
    """Tìm tất cả documents có field == value."""
    lock = _get_lock(collection)
    with lock:
        records = _load(collection)
    return [r for r in records if r.get(field) == value]


def find_one_by_field(collection: str, field: str, value: Any) -> dict | None:
    """Tìm document đầu tiên có field == value. None nếu không thấy."""
    lock = _get_lock(collection)
    with lock:
        records = _load(collection)
    return next((r for r in records if r.get(field) == value), None)

"""Repository quản lý kho thuốc.

Lưu trữ medicines dưới collection "medicines" với cấu trúc tối thiểu:
{
  "_id": "...",
  "name": "NAME",
  "dosage": "500 MG",
  "unit": "viên",
  "quantity_number": 20,
  "quantity_raw": "20 viên"
}

Hỗ trợ parsing các dạng quantity như "20 viên", "2 vỉ x 10 viên", "2x10 viên".
Khi giảm lượng sẽ ghi audit vào collection "medicine_audit".
"""

from typing import Optional, Tuple
import re
from datetime import datetime

from app.database import json_store

COLLECTION = "medicines"
AUDIT_COLLECTION = "medicine_audit"


def _norm(s: str) -> str:
    return (s or "").strip().upper()


def _parse_quantity(raw: str) -> Tuple[int, str, str]:
    """Parse quantity string trả về (number, unit, raw).

    Hỗ trợ:
      - "20 viên" -> (20, "viên", "20 viên")
      - "2 vỉ x 10 viên" -> (20, "viên", "2 vỉ x 10 viên")
      - "2x10 viên" -> (20, "viên", "2x10 viên")
    Nếu không parse được số trả về (0, raw, raw).
    """
    if not raw:
        return 0, "", ""
    s = raw.strip()

    # pattern multiplier: 2 vỉ x 10 viên OR 2x10 viên OR 2 x 10 viên
    m = re.search(r"(\d+)\s*(?:V[IỈ]?[AÁ]?|V[IỈ])?\s*[x×*]\s*(\d+)\s*([^\d].*)?", s, flags=re.IGNORECASE)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        unit = (m.group(3) or "").strip()
        return a * b, unit, s

    # pattern simple: 20 viên
    m2 = re.match(r"\s*(\d+)\s*([^\d].*)?", s)
    if m2:
        num = int(m2.group(1))
        unit = (m2.group(2) or "").strip()
        return num, unit, s

    return 0, "", s


def _find_by_key(name: str, dosage: str, unit: str) -> Optional[dict]:
    name_n = _norm(name)
    dosage_n = _norm(dosage)
    unit_n = (unit or "").strip().lower()
    records = json_store.find_all(COLLECTION)
    for r in records:
        if r.get("name") == name_n and _norm(r.get("dosage", "")) == dosage_n and (r.get("unit", "") or "").lower() == unit_n:
            return r
    return None


def upsert_from_prescription_item(item: dict) -> dict:
    """Upsert thuốc từ item của prescription. Trả về document (mới hoặc existing)."""
    name = item.get("name", "")
    dosage = item.get("dosage", "")
    qty_raw = item.get("quantity", "")
    number, unit, raw = _parse_quantity(qty_raw)

    if not name:
        return {}

    name_n = _norm(name)
    dosage_n = dosage or ""
    unit_n = unit or ""

    existing = _find_by_key(name_n, dosage_n, unit_n)
    if existing:
        # cộng số lượng
        cur = int(existing.get("quantity_number", 0) or 0)
        new = cur + (number or 0)
        updated = json_store.update_by_id(COLLECTION, existing["_id"], {"quantity_number": new, "quantity_raw": f"{new} {unit_n}".strip(), "unit": unit_n})
        return updated

    doc = {
        "_id": str(__import__("uuid").uuid4()),
        "name": name_n,
        "dosage": dosage_n,
        "unit": unit_n,
        "quantity_number": number,
        "quantity_raw": raw or qty_raw,
    }
    return json_store.insert(COLLECTION, doc)


def decrease_quantity(name: str, dosage: str = "", unit: str = "", amount: int = 1, *, prescription_id: str | None = None, reminder_id: str | None = None) -> Optional[dict]:
    """Giảm `quantity_number` của một medicine theo composite key.

    Ghi audit vào `medicine_audit` với context prescription_id, reminder_id.
    Trả về document cập nhật hoặc None.
    """
    existing = _find_by_key(name, dosage, unit)
    if not existing:
        return None

    cur = int(existing.get("quantity_number", 0) or 0)
    new = max(cur - amount, 0)
    updated = json_store.update_by_id(COLLECTION, existing["_id"], {"quantity_number": new, "quantity_raw": f"{new} {existing.get('unit','')}".strip()})

    # audit
    audit = {
        "_id": str(__import__("uuid").uuid4()),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "medicine_id": existing.get("_id"),
        "medicine_name": existing.get("name"),
        "dosage": existing.get("dosage"),
        "unit": existing.get("unit"),
        "change": -int(amount),
        "from_quantity": cur,
        "to_quantity": new,
        "prescription_id": prescription_id or "",
        "reminder_id": reminder_id or "",
    }
    try:
        json_store.insert(AUDIT_COLLECTION, audit)
    except Exception:
        pass

    return updated


def get_all() -> list[dict]:
    return json_store.find_all(COLLECTION)


def create(data: dict) -> dict:
    """Tạo một document medicine mới (không upsert)."""
    name = data.get("name", "")
    dosage = data.get("dosage", "")
    unit = data.get("unit", "")
    qty_num = int(data.get("quantity_number", 0) or 0)
    qty_raw = data.get("quantity_raw", f"{qty_num} {unit}".strip())

    doc = {
        "_id": str(__import__("uuid").uuid4()),
        "name": _norm(name),
        "dosage": dosage or "",
        "unit": unit or "",
        "quantity_number": qty_num,
        "quantity_raw": qty_raw,
    }
    return json_store.insert(COLLECTION, doc)


def find_by_key(name: str, dosage: str = "", unit: str = "") -> Optional[dict]:
    return _find_by_key(name, dosage, unit)


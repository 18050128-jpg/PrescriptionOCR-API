"""
Domain model cho Reminder — lịch nhắc uống thuốc.
"""

from typing import Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class Reminder(BaseModel):
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    user_id: str                         # Chủ reminder
    prescription_id: str                 # Toa thuốc liên quan
    medicine_name: str                   # Tên thuốc cần nhắc
    remind_time: str                     # Giờ nhắc, format "HH:MM"
    days_of_week: list[int] = []         # 0=Thứ 2 ... 6=Chủ nhật; [] = mỗi ngày
    note: Optional[str] = None
    is_active: bool = True

    def to_document(self) -> dict:
        data = self.model_dump()
        data["_id"] = self._id
        data["created_at"] = self.created_at
        return data

    @classmethod
    def from_document(cls, doc: dict) -> "Reminder":
        obj = cls.model_validate(doc)
        object.__setattr__(obj, "_id", doc.get("_id", str(uuid.uuid4())))
        object.__setattr__(obj, "created_at", doc.get("created_at", ""))
        return obj

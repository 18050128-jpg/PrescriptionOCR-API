"""
Pydantic schemas cho Reminder API.
"""

import re
from typing import Optional
from pydantic import BaseModel, field_validator


class ReminderCreate(BaseModel):
    prescription_id: str
    medicine_name: str
    remind_time: str           # "HH:MM"
    days_of_week: list[int] = []   # [] = mỗi ngày; 0=T2 .. 6=CN
    note: Optional[str] = None

    @field_validator("remind_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("remind_time phải có format HH:MM (ví dụ: 08:00)")
        h, m = map(int, v.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Giờ hoặc phút không hợp lệ")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("days_of_week phải là số từ 0 (T2) đến 6 (CN)")
        return sorted(set(v))


class ReminderUpdate(BaseModel):
    medicine_name: Optional[str] = None
    remind_time: Optional[str] = None
    days_of_week: Optional[list[int]] = None
    note: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("remind_time")
    @classmethod
    def validate_time(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("remind_time phải có format HH:MM")
        h, m = map(int, v.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Giờ hoặc phút không hợp lệ")
        return v


class ReminderResponse(BaseModel):
    model_config = {"from_attributes": True}

    _id: str
    created_at: str
    user_id: str
    prescription_id: str
    medicine_name: str
    remind_time: str
    days_of_week: list[int]
    note: Optional[str]
    is_active: bool

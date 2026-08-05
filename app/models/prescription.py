"""
Domain model cho Prescription — ánh xạ trực tiếp với document JSON được lưu.
"""

from typing import Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class Medicine(BaseModel):
    name: str = ""
    dosage: str = ""
    quantity: str = ""
    remaining: str = ""
    usage: str = ""
    reminder_times: list[str] = []


class Prescription(BaseModel):
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    # Liên kết với user
    user_id: Optional[str] = None

    # Thông tin từ extraction
    hospital: Optional[str] = None
    patient_name: Optional[str] = None
    doctor: Optional[str] = None
    diagnosis: Optional[str] = None
    date: Optional[str] = None
    medicines: list[Medicine] = []
    prescription_type: Optional[str] = None  # "bhyt" | "handwritten" | "unknown"

    # Metadata file ảnh
    filename: str = ""
    image_path: str = ""

    def to_document(self) -> dict:
        """Chuyển sang dict để lưu vào JSON store."""
        data = self.model_dump()
        data["_id"] = self._id
        data["created_at"] = self.created_at
        return data

    @classmethod
    def from_document(cls, doc: dict) -> "Prescription":
        """Phục hồi object từ dict đọc ra từ JSON store."""
        obj = cls.model_validate(doc)
        object.__setattr__(obj, "_id", doc.get("_id", str(uuid.uuid4())))
        object.__setattr__(obj, "created_at", doc.get("created_at", ""))
        return obj

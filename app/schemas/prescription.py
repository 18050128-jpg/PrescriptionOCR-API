"""
Pydantic schemas cho API request/response.
"""

from typing import Optional
from pydantic import BaseModel


class MedicineSchema(BaseModel):
    name: str
    dosage: str
    quantity: str
    remaining: str
    usage: str
    reminder_times: list[str] = []


class PrescriptionResponse(BaseModel):
    """Response schema cho prescription với metadata đầy đủ."""
    model_config = {"from_attributes": True}

    _id: str
    created_at: str

    hospital: Optional[str] = None
    patient_name: Optional[str] = None
    doctor: Optional[str] = None
    diagnosis: Optional[str] = None
    date: Optional[str] = None
    medicines: list[MedicineSchema] = []
    prescription_type: Optional[str] = None

    filename: str
    image_path: str


class PrescriptionListResponse(BaseModel):
    """Response cho endpoint list prescriptions."""
    total: int
    prescriptions: list[PrescriptionResponse]


class UploadOCRExtractResponse(BaseModel):
    """Response cho endpoint upload OCR extract."""
    status: str
    prescription: PrescriptionResponse

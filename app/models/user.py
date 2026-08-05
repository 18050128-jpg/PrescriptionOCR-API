"""
Domain model cho User.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class UserRole(str, Enum):
    admin = "admin"
    user  = "user"


class User(BaseModel):
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    username: str
    email: str
    hashed_password: str
    role: UserRole = UserRole.user
    is_active: bool = True
    full_name: Optional[str] = None

    def to_document(self) -> dict:
        data = self.model_dump()
        data["_id"] = self._id
        data["created_at"] = self.created_at
        return data

    @classmethod
    def from_document(cls, doc: dict) -> "User":
        obj = cls.model_validate(doc)
        object.__setattr__(obj, "_id", doc.get("_id", str(uuid.uuid4())))
        object.__setattr__(obj, "created_at", doc.get("created_at", ""))
        return obj

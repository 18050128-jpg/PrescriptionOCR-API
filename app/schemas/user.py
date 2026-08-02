"""
Pydantic schemas cho Auth & User API.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("username phải có ít nhất 3 ký tự")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("username chỉ được chứa chữ, số, dấu _ hoặc -")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("password phải có ít nhất 6 ký tự")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """Thông tin user trả về cho client (không có hashed_password)."""
    model_config = {"populate_by_name": True}

    id: str = Field(alias="_id", default="")
    created_at: str = ""
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool

    @property
    def _id(self) -> str:
        return self.id


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict  # dùng dict để tránh Pydantic serialize bỏ _id

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    # ─── User fields ─────────────────────────────────────────
    email: EmailStr
    password: str

    # ─── Student fields ──────────────────────────────────────
    mssv: str
    full_name: str
    faculty: str
    major: str
    cohort: int

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự")
        return v

    @field_validator("mssv")
    @classmethod
    def mssv_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("MSSV không được để trống")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str    # user_id as string
    role: str

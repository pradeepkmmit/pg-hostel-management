import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    room_type: str
    description: str
    monthly_rent: int
    available: bool
    tag: str


class InquiryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    message: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must contain at least one non-space character")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        return value.strip()


class InquiryResponse(BaseModel):
    id: int
    message: str


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    phone: str = Field(default="", max_length=30)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("name")
    @classmethod
    def normalize_user_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must contain at least one non-space character")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_user_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    role: Literal["resident", "admin"]
    active: bool


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(default="", max_length=30)

    @field_validator("name")
    @classmethod
    def normalize_profile_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must contain at least one non-space character")
        return normalized

    @field_validator("phone")
    @classmethod
    def normalize_profile_phone(cls, value: str) -> str:
        return value.strip()


class BookingCreate(BaseModel):
    room_id: int = Field(gt=0)
    move_in_date: date | None = None
    message: str = Field(default="", max_length=1000)

    @field_validator("move_in_date")
    @classmethod
    def validate_move_in_date(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("Move-in date cannot be in the past")
        return value

    @field_validator("message")
    @classmethod
    def normalize_booking_message(cls, value: str) -> str:
        return value.strip()


class BookingStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]


class BookingResponse(BaseModel):
    id: int
    room_id: int
    room_name: str
    move_in_date: date | None
    message: str
    status: Literal["pending", "approved", "rejected"]
    created_at: str
    resident_name: str | None = None
    resident_email: str | None = None


class MaintenanceCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("category", "description")
    @classmethod
    def normalize_maintenance_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field must contain non-space characters")
        return normalized


class MaintenanceStatusUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved"]


class MaintenanceResponse(BaseModel):
    id: int
    user_id: int
    category: str
    description: str
    status: Literal["open", "in_progress", "resolved"]
    created_at: str
    resident_name: str | None = None


class PaymentCreate(BaseModel):
    user_id: int = Field(gt=0)
    amount: int = Field(gt=0, le=100_000_000)
    billing_period: str = Field(min_length=1, max_length=30)
    due_date: date
    status: Literal["due", "paid"] = "due"
    note: str = Field(default="", max_length=500)

    @field_validator("billing_period", "note")
    @classmethod
    def normalize_payment_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_billing_period(self) -> "PaymentCreate":
        if not self.billing_period:
            raise ValueError("Billing period cannot be blank")
        return self


class PaymentStatusUpdate(BaseModel):
    status: Literal["due", "paid"]


class NoticeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=3000)

    @field_validator("title", "message")
    @classmethod
    def normalize_notice_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field must contain non-space characters")
        return normalized


class NoticeResponse(BaseModel):
    id: int
    title: str
    message: str
    author_name: str
    created_at: str

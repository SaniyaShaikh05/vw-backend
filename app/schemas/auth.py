from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
import uuid

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    hospital: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: uuid.UUID
    role: str
    full_name: Optional[str] = None
    profile: Optional[dict] = None

class MessageResponse(BaseModel):
    message: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

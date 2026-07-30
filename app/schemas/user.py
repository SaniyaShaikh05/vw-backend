from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
import uuid

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    role: str

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class PatientProfileUpdate(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    diabetes_type: Optional[str] = None
    medications: Optional[list] = None
    emergency_contact: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None

class PatientProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    diabetes_type: Optional[str] = None
    medications: Optional[list] = None
    emergency_contact: Optional[str] = None
    assigned_doctor_id: Optional[uuid.UUID] = None
    glucose_min_threshold: float
    glucose_max_threshold: float
    user: UserResponse

    class Config:
        from_attributes = True

class DoctorProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    hospital: Optional[str] = None
    is_verified: bool
    user: UserResponse

    class Config:
        from_attributes = True

class PatientThresholdsUpdate(BaseModel):
    glucose_min_threshold: float
    glucose_max_threshold: float

import uuid
from sqlalchemy import Column, String, Boolean, Date, Float, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.types import DateTime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # 'patient', 'doctor', 'admin'
    full_name = Column(String(255))
    phone = Column(String(20))
    date_of_birth = Column(Date)
    gender = Column(String(10))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    height_cm = Column(Float)
    weight_kg = Column(Float)
    diabetes_type = Column(String(20))  # 'type1', 'type2', 'prediabetic', 'none'
    medications = Column(JSONB, default=list)
    emergency_contact = Column(String(255))
    assigned_doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    glucose_min_threshold = Column(Float, default=70.0)
    glucose_max_threshold = Column(Float, default=180.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="patient_profile", foreign_keys=[user_id])
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_id])

class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    specialization = Column(String(100))
    license_number = Column(String(100))
    hospital = Column(String(255))
    is_verified = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="doctor_profile")

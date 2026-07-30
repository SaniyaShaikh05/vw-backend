import uuid
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reading_id = Column(UUID(as_uuid=True), ForeignKey("readings.id"), nullable=True)
    alert_type = Column(String(50))
    severity = Column(String(20))
    value = Column(Float)
    threshold = Column(Float)
    message = Column(Text)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reading_id = Column(UUID(as_uuid=True), ForeignKey("readings.id"), nullable=True)
    note_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

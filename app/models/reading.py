import uuid
from sqlalchemy import Column, String, Float, Integer, SmallInteger, ForeignKey, Index, desc
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from app.database import Base

class Reading(Base):
    __tablename__ = "readings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    local_id = Column(String(100), unique=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    glucose_mgdl = Column(Float)
    systolic_mmhg = Column(Float)
    diastolic_mmhg = Column(Float)
    heart_rate_bpm = Column(Float)
    spo2_percent = Column(Float)
    signal_quality = Column(SmallInteger)
    measurement_duration_sec = Column(Integer)
    hrv_features = Column(JSONB)
    synced_from = Column(String(20), default="app")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_readings_patient_time", "patient_id", timestamp.desc(), postgresql_using="btree"),
    )

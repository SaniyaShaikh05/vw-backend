import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from app.database import Base

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    ble_mac = Column(String(20), unique=True)
    device_name = Column(String(100))
    firmware_version = Column(String(20))
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

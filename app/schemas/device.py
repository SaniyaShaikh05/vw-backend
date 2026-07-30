from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class DeviceRegister(BaseModel):
    ble_mac: str
    device_name: str
    firmware_version: str

class DeviceResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    ble_mac: str
    device_name: str
    firmware_version: str
    is_active: bool
    last_seen: Optional[datetime] = None
    registered_at: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class AlertResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    reading_id: Optional[uuid.UUID] = None
    alert_type: str
    severity: str
    value: float
    threshold: float
    message: str
    is_acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ClinicalNoteCreate(BaseModel):
    note_text: str
    reading_id: Optional[uuid.UUID] = None

class ClinicalNoteResponse(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    reading_id: Optional[uuid.UUID] = None
    note_text: str
    created_at: datetime

    class Config:
        from_attributes = True

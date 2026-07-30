from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from app.schemas.device import DeviceResponse

class ReadingCreate(BaseModel):
    local_id: str
    timestamp: int  # Unix ms
    glucose_mgdl: Optional[float] = None
    systolic_mmhg: Optional[float] = None
    diastolic_mmhg: Optional[float] = None
    heart_rate_bpm: Optional[float] = None
    spo2_percent: Optional[float] = None
    signal_quality: Optional[int] = None
    measurement_duration_sec: Optional[int] = None
    hrv_features: Optional[Dict[str, Any]] = None
    device_ble_mac: Optional[str] = None

class SyncRequest(BaseModel):
    readings: List[ReadingCreate] = Field(..., max_length=100)

class SyncResponse(BaseModel):
    synced: int
    skipped: int
    failed: List[str]

class ReadingResponse(BaseModel):
    id: uuid.UUID
    local_id: str
    patient_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None
    timestamp: datetime
    glucose_mgdl: Optional[float] = None
    systolic_mmhg: Optional[float] = None
    diastolic_mmhg: Optional[float] = None
    heart_rate_bpm: Optional[float] = None
    spo2_percent: Optional[float] = None
    signal_quality: Optional[int] = None
    measurement_duration_sec: Optional[int] = None
    hrv_features: Optional[Dict[str, Any]] = None
    synced_from: str
    created_at: datetime

    class Config:
        from_attributes = True

class PatientDashboardResponse(BaseModel):
    latest_reading: Optional[ReadingResponse] = None
    today_avg_glucose: Optional[float] = None
    today_readings_count: int = 0
    time_in_range_percent: Optional[float] = None
    last_7_days_avg: Optional[float] = None
    active_alerts_count: int = 0
    device: Optional[DeviceResponse] = None

class SummaryStatsResponse(BaseModel):
    avg_glucose: Optional[float] = None
    min_glucose: Optional[float] = None
    max_glucose: Optional[float] = None
    time_in_range_percent: Optional[float] = None
    time_in_hypo_percent: Optional[float] = None
    time_in_hyper_percent: Optional[float] = None
    avg_systolic: Optional[float] = None
    avg_diastolic: Optional[float] = None
    avg_heart_rate: Optional[float] = None
    total_readings: int = 0
    readings_per_day: Optional[float] = None

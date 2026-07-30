from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.dependencies import get_current_user, get_current_patient
from app.models.user import User, PatientProfile
from app.models.device import Device
from app.models.reading import Reading
from app.schemas.reading import SyncRequest, SyncResponse, ReadingResponse, SummaryStatsResponse
from app.services.alert_service import check_and_create_alerts
from typing import List
import io
import csv

router = APIRouter(prefix="/api/v1/readings", tags=["readings"])

@router.post("/sync", response_model=SyncResponse)
async def sync_readings(
    request: SyncRequest,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    synced = 0
    skipped = 0
    failed = []
    
    # Get patient profile for alert logic
    prof_res = await db.execute(select(PatientProfile).where(PatientProfile.user_id == current_user.id))
    patient_profile = prof_res.scalars().first()
    
    # Cache device lookups
    devices_cache = {}
    
    for r in request.readings:
        # Resolve device ID
        device_id = None
        if r.device_ble_mac:
            if r.device_ble_mac not in devices_cache:
                d_res = await db.execute(select(Device).where(Device.ble_mac == r.device_ble_mac))
                device = d_res.scalars().first()
                if device:
                    devices_cache[r.device_ble_mac] = device.id
                else:
                    devices_cache[r.device_ble_mac] = None
            device_id = devices_cache[r.device_ble_mac]
            
        reading_ts = datetime.fromtimestamp(r.timestamp / 1000.0, timezone.utc)
        
        reading = Reading(
            local_id=r.local_id,
            patient_id=current_user.id,
            device_id=device_id,
            timestamp=reading_ts,
            glucose_mgdl=r.glucose_mgdl,
            systolic_mmhg=r.systolic_mmhg,
            diastolic_mmhg=r.diastolic_mmhg,
            heart_rate_bpm=r.heart_rate_bpm,
            spo2_percent=r.spo2_percent,
            signal_quality=r.signal_quality,
            measurement_duration_sec=r.measurement_duration_sec,
            hrv_features=r.hrv_features,
            synced_from="app"
        )
        
        try:
            db.add(reading)
            await db.commit()
            await db.refresh(reading)
            synced += 1
            
            # Check alerts
            await check_and_create_alerts(db, reading, patient_profile)
            await db.commit()
            
        except IntegrityError:
            await db.rollback()
            skipped += 1
        except Exception:
            await db.rollback()
            failed.append(r.local_id)
            
    return SyncResponse(synced=synced, skipped=skipped, failed=failed)

@router.get("/", response_model=List[ReadingResponse])
async def get_readings(
    patient_id: str = None,
    from_date: datetime = None,
    to_date: datetime = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    target_patient_id = patient_id if patient_id else str(current_user.id)
    
    if current_user.role == "patient" and target_patient_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Can only access own readings")
        
    if current_user.role == "doctor":
        prof = await db.execute(select(PatientProfile).where(PatientProfile.user_id == target_patient_id, PatientProfile.assigned_doctor_id == current_user.id))
        if not prof.scalars().first():
            raise HTTPException(status_code=403, detail="Patient not assigned to you")
            
    query = select(Reading).where(Reading.patient_id == target_patient_id).order_by(desc(Reading.timestamp)).limit(limit).offset(offset)
    if from_date:
        query = query.where(Reading.timestamp >= from_date)
    if to_date:
        query = query.where(Reading.timestamp <= to_date)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/summary", response_model=SummaryStatsResponse)
async def get_summary(
    patient_id: str = None,
    period: str = Query("7d", regex="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    target_patient_id = patient_id if patient_id else str(current_user.id)
    
    if current_user.role == "patient" and target_patient_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Can only access own readings")
        
    if current_user.role == "doctor":
        prof = await db.execute(select(PatientProfile).where(PatientProfile.user_id == target_patient_id, PatientProfile.assigned_doctor_id == current_user.id))
        if not prof.scalars().first():
            raise HTTPException(status_code=403, detail="Patient not assigned to you")
            
    days = int(period.replace("d", ""))
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    stats_res = await db.execute(
        select(
            func.avg(Reading.glucose_mgdl),
            func.min(Reading.glucose_mgdl),
            func.max(Reading.glucose_mgdl),
            func.avg(Reading.systolic_mmhg),
            func.avg(Reading.diastolic_mmhg),
            func.avg(Reading.heart_rate_bpm),
            func.count(Reading.id)
        ).where(
            Reading.patient_id == target_patient_id,
            Reading.timestamp >= start_date
        )
    )
    avg_gl, min_gl, max_gl, avg_sys, avg_dia, avg_hr, count = stats_res.first()
    
    tir_res = await db.execute(
        select(
            func.count(Reading.id).filter(Reading.glucose_mgdl >= 70, Reading.glucose_mgdl <= 180),
            func.count(Reading.id).filter(Reading.glucose_mgdl < 70),
            func.count(Reading.id).filter(Reading.glucose_mgdl > 180),
            func.count(Reading.id)
        ).where(
            Reading.patient_id == target_patient_id,
            Reading.timestamp >= start_date
        )
    )
    in_range, hypo, hyper, total = tir_res.first()
    
    return SummaryStatsResponse(
        avg_glucose=avg_gl,
        min_glucose=min_gl,
        max_glucose=max_gl,
        time_in_range_percent=(in_range / total * 100) if total else None,
        time_in_hypo_percent=(hypo / total * 100) if total else None,
        time_in_hyper_percent=(hyper / total * 100) if total else None,
        avg_systolic=avg_sys,
        avg_diastolic=avg_dia,
        avg_heart_rate=avg_hr,
        total_readings=count or 0,
        readings_per_day=(count / days) if count else 0
    )

@router.get("/export")
async def export_readings(
    patient_id: str = None,
    from_date: datetime = None,
    to_date: datetime = None,
    format: str = Query("csv"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    target_patient_id = patient_id if patient_id else str(current_user.id)
    
    if current_user.role == "patient" and target_patient_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Can only access own readings")
        
    query = select(Reading).where(Reading.patient_id == target_patient_id).order_by(Reading.timestamp)
    if from_date:
        query = query.where(Reading.timestamp >= from_date)
    if to_date:
        query = query.where(Reading.timestamp <= to_date)
        
    result = await db.execute(query)
    readings = result.scalars().all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "glucose_mgdl", "systolic_mmhg", "diastolic_mmhg", "heart_rate_bpm", "spo2_percent"])
    
    for r in readings:
        writer.writerow([r.timestamp.isoformat(), r.glucose_mgdl, r.systolic_mmhg, r.diastolic_mmhg, r.heart_rate_bpm, r.spo2_percent])
        
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=readings_{target_patient_id}.csv"})

@router.get("/{id}", response_model=ReadingResponse)
async def get_reading(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Reading).where(Reading.id == id))
    reading = result.scalars().first()
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
        
    if current_user.role == "patient" and str(reading.patient_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Can only access own readings")
        
    if current_user.role == "doctor":
        prof = await db.execute(select(PatientProfile).where(PatientProfile.user_id == reading.patient_id, PatientProfile.assigned_doctor_id == current_user.id))
        if not prof.scalars().first():
            raise HTTPException(status_code=403, detail="Patient not assigned to you")
            
    return reading

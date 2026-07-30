from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, func
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.dependencies import get_current_patient
from app.models.user import User, PatientProfile
from app.models.reading import Reading
from app.models.alert import Alert
from app.models.device import Device
from app.schemas.user import PatientProfileResponse, PatientProfileUpdate
from app.schemas.reading import PatientDashboardResponse, ReadingResponse
from app.schemas.device import DeviceResponse
from app.schemas.alert import AlertResponse
from typing import List

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])

@router.get("/profile", response_model=PatientProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    profile_dict = profile.__dict__.copy()
    profile_dict['user'] = current_user
    return profile_dict

@router.put("/profile", response_model=PatientProfileResponse)
async def update_profile(
    request: PatientProfileUpdate,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    # Update user fields
    user_updates = {}
    if request.full_name is not None: user_updates['full_name'] = request.full_name
    if request.phone is not None: user_updates['phone'] = request.phone
    if request.date_of_birth is not None: user_updates['date_of_birth'] = request.date_of_birth
    if request.gender is not None: user_updates['gender'] = request.gender
    
    if user_updates:
        await db.execute(update(User).where(User.id == current_user.id).values(**user_updates))

    # Update profile fields
    prof_updates = {}
    if request.height_cm is not None: prof_updates['height_cm'] = request.height_cm
    if request.weight_kg is not None: prof_updates['weight_kg'] = request.weight_kg
    if request.diabetes_type is not None: prof_updates['diabetes_type'] = request.diabetes_type
    if request.medications is not None: prof_updates['medications'] = request.medications
    if request.emergency_contact is not None: prof_updates['emergency_contact'] = request.emergency_contact
    
    if prof_updates:
        await db.execute(update(PatientProfile).where(PatientProfile.user_id == current_user.id).values(**prof_updates))
        
    await db.commit()
    return await get_profile(current_user, db)

@router.get("/dashboard", response_model=PatientDashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)
    
    # Latest reading
    latest_res = await db.execute(
        select(Reading).where(Reading.patient_id == current_user.id).order_by(desc(Reading.timestamp)).limit(1)
    )
    latest_reading = latest_res.scalars().first()
    
    # Today stats
    today_res = await db.execute(
        select(
            func.avg(Reading.glucose_mgdl),
            func.count(Reading.id)
        ).where(
            Reading.patient_id == current_user.id,
            Reading.timestamp >= start_of_today
        )
    )
    today_avg, today_count = today_res.first()
    
    # Active alerts count
    alerts_res = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.patient_id == current_user.id,
            Alert.is_acknowledged == False
        )
    )
    active_alerts_count = alerts_res.scalar() or 0
    
    # 7 Days Stats
    seven_res = await db.execute(
        select(func.avg(Reading.glucose_mgdl)).where(
            Reading.patient_id == current_user.id,
            Reading.timestamp >= seven_days_ago
        )
    )
    last_7_days_avg = seven_res.scalar()
    
    # Device
    device_res = await db.execute(
        select(Device).where(Device.patient_id == current_user.id, Device.is_active == True).limit(1)
    )
    device = device_res.scalars().first()
    
    # Time in range 
    tir_res = await db.execute(
        select(
            func.count(Reading.id).filter(Reading.glucose_mgdl >= 70, Reading.glucose_mgdl <= 180),
            func.count(Reading.id)
        ).where(
            Reading.patient_id == current_user.id,
            Reading.timestamp >= seven_days_ago
        )
    )
    tir_in_range, tir_total = tir_res.first()
    tir_percent = (tir_in_range / tir_total * 100) if tir_total and tir_total > 0 else None

    return PatientDashboardResponse(
        latest_reading=latest_reading,
        today_avg_glucose=today_avg,
        today_readings_count=today_count or 0,
        time_in_range_percent=tir_percent,
        last_7_days_avg=last_7_days_avg,
        active_alerts_count=active_alerts_count,
        device=device
    )

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    query = select(Alert).where(Alert.patient_id == current_user.id).order_by(desc(Alert.created_at)).limit(limit).offset(offset)
    if unread_only:
        query = query.where(Alert.is_acknowledged == False)
    result = await db.execute(query)
    return result.scalars().all()

@router.put("/alerts/{id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    id: str,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Alert).where(Alert.id == id, Alert.patient_id == current_user.id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert

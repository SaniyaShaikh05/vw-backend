from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, func
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.dependencies import get_current_doctor
from app.models.user import User, DoctorProfile, PatientProfile
from app.models.reading import Reading
from app.models.alert import Alert, ClinicalNote
from app.schemas.user import DoctorProfileResponse, PatientProfileResponse, PatientThresholdsUpdate
from app.schemas.reading import ReadingResponse, SummaryStatsResponse
from app.schemas.alert import AlertResponse, ClinicalNoteCreate, ClinicalNoteResponse
from typing import List
import uuid

router = APIRouter(prefix="/api/v1/doctors", tags=["doctors"])

@router.get("/profile", response_model=DoctorProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    profile_dict = profile.__dict__.copy()
    profile_dict['user'] = current_user
    return profile_dict

@router.get("/patients")
async def get_patients(
    limit: int = 20,
    offset: int = 0,
    search: str = None,
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    query = select(PatientProfile, User).join(
        User,
        PatientProfile.user_id == User.id
    ).where(
        PatientProfile.assigned_doctor_id == current_user.id
    )
    if search:
        query = query.where(User.full_name.ilike(f"%{search}%"))
        
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    
    patients = []
    for prof, user in result.all():
        latest_reading = await db.execute(
            select(Reading).where(Reading.patient_id == user.id).order_by(desc(Reading.timestamp)).limit(1)
        )
        patients.append({
            "profile": {**prof.__dict__, "user": user},
            "latest_reading": latest_reading.scalars().first()
        })
    return patients

@router.get("/patients/{patient_id}")
async def get_patient_details(
    patient_id: str,
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    prof_res = await db.execute(
    select(PatientProfile, User).join(
        User,
        PatientProfile.user_id == User.id
    ).where(
        PatientProfile.user_id == patient_id,
        PatientProfile.assigned_doctor_id == current_user.id
    )
)
    res = prof_res.first()
    if not res:
        raise HTTPException(status_code=404, detail="Patient not found or not assigned to you")
        
    prof, user = res
    latest_reading = await db.execute(
        select(Reading).where(Reading.patient_id == user.id).order_by(desc(Reading.timestamp)).limit(1)
    )
    alerts = await db.execute(
        select(Alert).where(Alert.patient_id == user.id).order_by(desc(Alert.created_at)).limit(5)
    )
    
    return {
        "profile": {**prof.__dict__, "user": user},
        "latest_reading": latest_reading.scalars().first(),
        "recent_alerts": alerts.scalars().all()
    }

@router.get("/patients/{patient_id}/readings", response_model=List[ReadingResponse])
async def get_patient_readings(
    patient_id: str,
    from_date: datetime = None,
    to_date: datetime = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    # Verify assignment
    prof = await db.execute(select(PatientProfile).where(PatientProfile.user_id == patient_id, PatientProfile.assigned_doctor_id == current_user.id))
    if not prof.scalars().first():
        raise HTTPException(status_code=404, detail="Patient not found or not assigned")

    query = select(Reading).where(Reading.patient_id == patient_id).order_by(desc(Reading.timestamp)).limit(limit).offset(offset)
    if from_date:
        query = query.where(Reading.timestamp >= from_date)
    if to_date:
        query = query.where(Reading.timestamp <= to_date)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/patients/{patient_id}/summary", response_model=SummaryStatsResponse)
async def get_patient_summary(
    patient_id: str,
    period: str = Query("7d", regex="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    prof = await db.execute(select(PatientProfile).where(PatientProfile.user_id == patient_id, PatientProfile.assigned_doctor_id == current_user.id))
    if not prof.scalars().first():
        raise HTTPException(status_code=404, detail="Patient not found or not assigned")

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
            Reading.patient_id == patient_id,
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
            Reading.patient_id == patient_id,
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

@router.post("/patients/{patient_id}/notes", response_model=ClinicalNoteResponse)
async def create_clinical_note(
    patient_id: str,
    note: ClinicalNoteCreate,
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    new_note = ClinicalNote(
        doctor_id=current_user.id,
        patient_id=uuid.UUID(patient_id),
        reading_id=note.reading_id,
        note_text=note.note_text
    )
    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)
    return new_note

@router.get("/patients/{patient_id}/notes", response_model=List[ClinicalNoteResponse])
async def get_clinical_notes(
    patient_id: str,
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ClinicalNote).where(ClinicalNote.patient_id == patient_id, ClinicalNote.doctor_id == current_user.id)
        .order_by(desc(ClinicalNote.created_at))
    )
    return result.scalars().all()

@router.put("/patients/{patient_id}/thresholds", response_model=PatientProfileResponse)
async def update_thresholds(
    patient_id: str,
    thresholds: PatientThresholdsUpdate,
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    prof_res = await db.execute(select(PatientProfile, User).join(User).where(PatientProfile.user_id == patient_id, PatientProfile.assigned_doctor_id == current_user.id))
    res = prof_res.first()
    if not res:
        raise HTTPException(status_code=404, detail="Patient not found or not assigned")
    
    prof, user = res
    prof.glucose_min_threshold = thresholds.glucose_min_threshold
    prof.glucose_max_threshold = thresholds.glucose_max_threshold
    await db.commit()
    
    profile_dict = prof.__dict__.copy()
    profile_dict['user'] = user
    return profile_dict

@router.get("/alerts", response_model=List[AlertResponse])
async def get_doctor_alerts(
    patient_id: str = None,
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = True,
    current_user: User = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db)
):
    query = select(Alert).join(PatientProfile, Alert.patient_id == PatientProfile.user_id)\
            .where(PatientProfile.assigned_doctor_id == current_user.id)\
            .order_by(desc(Alert.created_at)).limit(limit).offset(offset)
            
    if patient_id:
        query = query.where(Alert.patient_id == patient_id)
    if unread_only:
        query = query.where(Alert.is_acknowledged == False)
        
    result = await db.execute(query)
    return result.scalars().all()

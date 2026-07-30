from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.alert import Alert
from app.models.reading import Reading
from app.models.user import PatientProfile
from datetime import datetime, timedelta, timezone

async def check_and_create_alerts(db: AsyncSession, reading: Reading, patient_profile: PatientProfile):
    alerts_to_create = []
    now = datetime.now(timezone.utc)
    
    # 1. Hypoglycemia
    if reading.glucose_mgdl is not None and reading.glucose_mgdl < patient_profile.glucose_min_threshold:
        val = reading.glucose_mgdl
        severity = "medium"
        if val < 55:
            severity = "critical"
        elif val < 65:
            severity = "high"
            
        alerts_to_create.append({
            "alert_type": "hypoglycemia",
            "severity": severity,
            "value": val,
            "threshold": patient_profile.glucose_min_threshold,
            "message": f"Low glucose level detected: {val} mg/dL"
        })

    # 2. Hyperglycemia
    if reading.glucose_mgdl is not None and reading.glucose_mgdl > patient_profile.glucose_max_threshold:
        val = reading.glucose_mgdl
        severity = "medium"
        if val > 300:
            severity = "critical"
        elif val > 250:
            severity = "high"
            
        alerts_to_create.append({
            "alert_type": "hyperglycemia",
            "severity": severity,
            "value": val,
            "threshold": patient_profile.glucose_max_threshold,
            "message": f"High glucose level detected: {val} mg/dL"
        })
        
    # 3. Irregular Heart Rate
    if reading.heart_rate_bpm is not None and (reading.heart_rate_bpm < 40 or reading.heart_rate_bpm > 150):
        val = reading.heart_rate_bpm
        alerts_to_create.append({
            "alert_type": "irregular_hr",
            "severity": "high",
            "value": val,
            "threshold": 150 if val > 150 else 40,
            "message": f"Irregular heart rate detected: {val} BPM"
        })

    # 4. Low SpO2
    if reading.spo2_percent is not None and reading.spo2_percent < 90:
        val = reading.spo2_percent
        severity = "critical" if val < 85 else "high"
        alerts_to_create.append({
            "alert_type": "low_spo2",
            "severity": severity,
            "value": val,
            "threshold": 90,
            "message": f"Low SpO2 detected: {val}%"
        })

    for alert_data in alerts_to_create:
        # Check for duplicates in last 30 mins
        thirty_mins_ago = now - timedelta(minutes=30)
        recent_alert = await db.execute(
            select(Alert).where(
                and_(
                    Alert.patient_id == reading.patient_id,
                    Alert.alert_type == alert_data["alert_type"],
                    Alert.created_at >= thirty_mins_ago
                )
            )
        )
        if recent_alert.scalars().first() is None:
            new_alert = Alert(
                patient_id=reading.patient_id,
                reading_id=reading.id,
                **alert_data
            )
            db.add(new_alert)

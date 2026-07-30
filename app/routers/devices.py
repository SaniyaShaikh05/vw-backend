from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.dependencies import get_current_patient
from app.models.user import User
from app.models.device import Device
from app.schemas.device import DeviceRegister, DeviceResponse
from app.schemas.auth import MessageResponse
from typing import List

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    request: DeviceRegister,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Device).where(Device.ble_mac == request.ble_mac))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="Device with this MAC already registered")
        
    device = Device(
        patient_id=current_user.id,
        ble_mac=request.ble_mac,
        device_name=request.device_name,
        firmware_version=request.firmware_version,
        last_seen=datetime.now(timezone.utc)
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device

@router.get("/", response_model=List[DeviceResponse])
async def get_devices(
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Device).where(Device.patient_id == current_user.id))
    return result.scalars().all()

@router.delete("/{id}", response_model=MessageResponse)
async def remove_device(
    id: str,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Device).where(Device.id == id, Device.patient_id == current_user.id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    await db.delete(device)
    await db.commit()
    return MessageResponse(message="device removed")

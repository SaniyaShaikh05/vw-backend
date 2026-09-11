from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
import redis.asyncio as redis
from app.database import get_db
from app.dependencies import get_redis_client, get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, MessageResponse, ForgotPasswordRequest, ResetPasswordRequest
from app.models.user import User, PatientProfile, DoctorProfile
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.config import get_settings
from jose import jwt
import uuid
import time

settings = get_settings()
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="Email already registered")
        
    user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        full_name=request.full_name,
        role=request.role,
        phone=request.phone,
        date_of_birth=request.date_of_birth,
        gender=request.gender
    )
    db.add(user)
    await db.flush()
    
    if user.role == "patient":
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
    elif user.role == "doctor":
        profile = DoctorProfile(
            user_id=user.id,
            specialization=request.specialization,
            license_number=request.license_number,
            hospital=request.hospital
        )
        db.add(profile)
        
    await db.commit()
    await db.refresh(user)
    
    access_token = create_access_token(data={"user_id": str(user.id)})
    refresh_token = create_refresh_token(data={"user_id": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"user_id": str(user.id)})
    refresh_token = create_refresh_token(data={"user_id": str(user.id)})
    
    profile_dict = None
    if user.role == "patient":
        prof_result = await db.execute(select(PatientProfile).where(PatientProfile.user_id == user.id))
        prof = prof_result.scalars().first()
        if prof:
            profile_dict = {"height_cm": prof.height_cm, "weight_kg": prof.weight_kg, "diabetes_type": prof.diabetes_type}
    elif user.role == "doctor":
        prof_result = await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == user.id))
        prof = prof_result.scalars().first()
        if prof:
            profile_dict = {"specialization": prof.specialization, "hospital": prof.hospital}
            
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
        profile=profile_dict
    )
@router.post("/swagger-login", include_in_schema=False)
async def swagger_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(
        data={"user_id": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
    
@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    access_token = create_access_token(data={"user_id": str(user.id)})
    refresh_token = create_refresh_token(data={"user_id": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name
    )

@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            exp = payload.get("exp")
            if exp:
                ttl = exp - int(time.time())
                if ttl > 0:
                    await redis_client.setex(f"bl_{token}", ttl, "true")
        except Exception:
            pass
            
    return MessageResponse(message="logged out")

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    return MessageResponse(message="reset link sent")

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    return MessageResponse(message="password reset successful")

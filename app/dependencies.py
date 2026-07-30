from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
import redis.asyncio as redis
from app.database import get_db
from app.config import get_settings
from app.core.exceptions import CredentialsException, ForbiddenException
from app.models.user import User
from sqlalchemy import select
import uuid

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_redis_client() -> redis.Redis:
    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield redis_client
    finally:
        await redis_client.aclose()

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
) -> User:
    # Check if token is blacklisted
    is_blacklisted = await redis_client.get(f"bl_{token}")
    if is_blacklisted:
        raise CredentialsException(detail="Token has been revoked")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise CredentialsException()
    except JWTError:
        raise CredentialsException()

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    
    if user is None:
        raise CredentialsException()
    if not user.is_active:
        raise CredentialsException(detail="Inactive user")
        
    return user

async def get_current_patient(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "patient":
        raise ForbiddenException(detail="Requires patient role")
    return current_user

async def get_current_doctor(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "doctor":
        raise ForbiddenException(detail="Requires doctor role")
    return current_user

async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise ForbiddenException(detail="Requires admin role")
    return current_user

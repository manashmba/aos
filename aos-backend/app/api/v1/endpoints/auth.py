"""
AOS Authentication Endpoints
Login, register, token refresh, and user management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import Organization, User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request / Response Schemas ──


class RegisterOrgRequest(BaseModel):
    org_name: str
    org_gstin: str = ""
    admin_name: str
    admin_email: EmailStr
    admin_password: str
    admin_phone: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    org_id: str
    org_name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    phone: str = ""
    department: str = ""
    location: str = ""
    language: str = "en"


# ── Endpoints ──


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_organization(body: RegisterOrgRequest, db: AsyncSession = Depends(get_db)):
    """Register a new organization and admin user."""

    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == body.admin_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create organization
    org = Organization(
        name=body.org_name,
        gstin=body.org_gstin,
        settings={},
    )
    db.add(org)
    await db.flush()

    # Create admin user
    user = User(
        org_id=org.id,
        name=body.admin_name,
        email=body.admin_email,
        password_hash=hash_password(body.admin_password),
        phone=body.admin_phone,
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        org_id=str(org.id),
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        org_id=str(org.id),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        role=user.role,
        org_id=str(org.id),
        org_name=org.name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and get tokens."""

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.add(user)

    # Get org name
    org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = org_result.scalar_one()

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        org_id=str(user.org_id),
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        org_id=str(user.org_id),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        role=user.role,
        org_id=str(user.org_id),
        org_name=org.name,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an access token."""
    try:
        payload = decode_token(body.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = org_result.scalar_one()

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        org_id=str(user.org_id),
    )
    new_refresh_token = create_refresh_token(
        subject=str(user.id),
        org_id=str(user.org_id),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user_id=str(user.id),
        role=user.role,
        org_id=str(user.org_id),
        org_name=org.name,
    )

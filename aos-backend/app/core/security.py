"""
AOS Security Module
JWT authentication, password hashing, and access control.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    role: str,
    org_id: str,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token with role and org context."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    payload = {
        "sub": subject,
        "role": role,
        "org_id": org_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, org_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": subject,
        "org_id": org_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


class Permission:
    """Permission constants for RBAC."""

    # Finance
    FINANCE_VIEW = "finance:view"
    FINANCE_CREATE = "finance:create"
    FINANCE_APPROVE = "finance:approve"
    FINANCE_ADMIN = "finance:admin"

    # Procurement
    PROCUREMENT_VIEW = "procurement:view"
    PROCUREMENT_CREATE = "procurement:create"
    PROCUREMENT_APPROVE = "procurement:approve"
    PROCUREMENT_ADMIN = "procurement:admin"

    # Inventory
    INVENTORY_VIEW = "inventory:view"
    INVENTORY_CREATE = "inventory:create"
    INVENTORY_ADJUST = "inventory:adjust"
    INVENTORY_ADMIN = "inventory:admin"

    # Sales
    SALES_VIEW = "sales:view"
    SALES_CREATE = "sales:create"
    SALES_APPROVE = "sales:approve"
    SALES_ADMIN = "sales:admin"

    # HR
    HR_VIEW = "hr:view"
    HR_CREATE = "hr:create"
    HR_APPROVE = "hr:approve"
    HR_ADMIN = "hr:admin"

    # Manufacturing
    MFG_VIEW = "manufacturing:view"
    MFG_CREATE = "manufacturing:create"
    MFG_APPROVE = "manufacturing:approve"
    MFG_ADMIN = "manufacturing:admin"

    # System
    SYSTEM_ADMIN = "system:admin"
    AUDIT_VIEW = "audit:view"
    POLICY_MANAGE = "policy:manage"
    AGENT_MANAGE = "agent:manage"


# Default role → permissions mapping
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "ceo": [
        Permission.FINANCE_VIEW, Permission.FINANCE_APPROVE,
        Permission.PROCUREMENT_VIEW, Permission.PROCUREMENT_APPROVE,
        Permission.INVENTORY_VIEW, Permission.SALES_VIEW, Permission.SALES_APPROVE,
        Permission.HR_VIEW, Permission.MFG_VIEW, Permission.AUDIT_VIEW,
        Permission.POLICY_MANAGE,
    ],
    "cfo": [
        Permission.FINANCE_VIEW, Permission.FINANCE_CREATE, Permission.FINANCE_APPROVE,
        Permission.FINANCE_ADMIN, Permission.PROCUREMENT_VIEW, Permission.PROCUREMENT_APPROVE,
        Permission.SALES_VIEW, Permission.AUDIT_VIEW, Permission.POLICY_MANAGE,
    ],
    "procurement_manager": [
        Permission.PROCUREMENT_VIEW, Permission.PROCUREMENT_CREATE,
        Permission.PROCUREMENT_APPROVE, Permission.INVENTORY_VIEW,
    ],
    "procurement_executive": [
        Permission.PROCUREMENT_VIEW, Permission.PROCUREMENT_CREATE,
        Permission.INVENTORY_VIEW,
    ],
    "finance_manager": [
        Permission.FINANCE_VIEW, Permission.FINANCE_CREATE, Permission.FINANCE_APPROVE,
        Permission.PROCUREMENT_VIEW, Permission.SALES_VIEW, Permission.AUDIT_VIEW,
    ],
    "finance_executive": [
        Permission.FINANCE_VIEW, Permission.FINANCE_CREATE,
    ],
    "sales_head": [
        Permission.SALES_VIEW, Permission.SALES_CREATE, Permission.SALES_APPROVE,
        Permission.INVENTORY_VIEW, Permission.FINANCE_VIEW,
    ],
    "sales_executive": [
        Permission.SALES_VIEW, Permission.SALES_CREATE,
    ],
    "warehouse_manager": [
        Permission.INVENTORY_VIEW, Permission.INVENTORY_CREATE, Permission.INVENTORY_ADJUST,
        Permission.INVENTORY_ADMIN, Permission.PROCUREMENT_VIEW,
    ],
    "warehouse_staff": [
        Permission.INVENTORY_VIEW, Permission.INVENTORY_CREATE,
    ],
    "hr_manager": [
        Permission.HR_VIEW, Permission.HR_CREATE, Permission.HR_APPROVE, Permission.HR_ADMIN,
    ],
    "employee": [
        Permission.HR_VIEW, Permission.HR_CREATE,
    ],
    "production_manager": [
        Permission.MFG_VIEW, Permission.MFG_CREATE, Permission.MFG_APPROVE,
        Permission.INVENTORY_VIEW,
    ],
    "auditor": [
        Permission.FINANCE_VIEW, Permission.PROCUREMENT_VIEW, Permission.INVENTORY_VIEW,
        Permission.SALES_VIEW, Permission.AUDIT_VIEW,
    ],
    "admin": [
        Permission.SYSTEM_ADMIN, Permission.AUDIT_VIEW, Permission.POLICY_MANAGE,
        Permission.AGENT_MANAGE,
    ],
}

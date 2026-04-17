"""
AOS Dependency Injection
FastAPI dependencies for auth, database, and services.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import ROLE_PERMISSIONS, decode_token

security_scheme = HTTPBearer()


class CurrentUser:
    """Represents the authenticated user from JWT."""

    def __init__(self, user_id: str, role: str, org_id: str, permissions: list[str]):
        self.user_id = user_id
        self.role = role
        self.org_id = org_id
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def require_permission(self, permission: str):
        if not self.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required",
            )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
) -> CurrentUser:
    """Extract and validate the current user from the JWT token."""
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    role = payload.get("role", "employee")
    org_id = payload.get("org_id", "")

    permissions = ROLE_PERMISSIONS.get(role, [])

    return CurrentUser(
        user_id=user_id,
        role=role,
        org_id=org_id,
        permissions=permissions,
    )


# Type aliases for cleaner endpoint signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(*roles: str):
    """Dependency factory that requires the user to have one of the specified roles."""
    async def _check(user: AuthUser) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role} not authorized. Required: {', '.join(roles)}",
            )
        return user
    return _check


def require_permission(permission: str):
    """Dependency factory that requires a specific permission."""
    async def _check(user: AuthUser) -> CurrentUser:
        user.require_permission(permission)
        return user
    return _check

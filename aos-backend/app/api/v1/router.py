"""
AOS API V1 Router
Central router that includes all endpoint modules.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    auth,
    conversation,
    finance,
    health,
    inventory,
    policy,
    procurement,
)

api_router = APIRouter()

# Core routes
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(policy.router)
api_router.include_router(agents.router)
api_router.include_router(conversation.router)

# Domain routes
api_router.include_router(finance.router)
api_router.include_router(procurement.router)
api_router.include_router(inventory.router)

# Added in later modules:
# api_router.include_router(sales.router)
# api_router.include_router(manufacturing.router)
# api_router.include_router(hr.router)
# api_router.include_router(approvals.router)
# api_router.include_router(audit.router)

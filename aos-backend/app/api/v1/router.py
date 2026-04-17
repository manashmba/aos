"""
AOS API V1 Router
Central router that includes all endpoint modules.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health

api_router = APIRouter()

# Core routes
api_router.include_router(health.router)
api_router.include_router(auth.router)

# Domain routes added as modules are built:
# api_router.include_router(conversation.router)
# api_router.include_router(procurement.router)
# api_router.include_router(finance.router)
# api_router.include_router(inventory.router)
# api_router.include_router(sales.router)
# api_router.include_router(manufacturing.router)
# api_router.include_router(hr.router)
# api_router.include_router(approvals.router)
# api_router.include_router(audit.router)
# api_router.include_router(policy.router)
# api_router.include_router(agents.router)

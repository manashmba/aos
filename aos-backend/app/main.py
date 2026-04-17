"""
AOS — Agentic Operating System
Main FastAPI Application Entry Point.

The ERP Replacement for the AI Era.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.bootstrap import bootstrap_agents
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.redis import close_redis
from app.middleware.audit import AuditMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown events."""
    setup_logging()
    bootstrap_agents()
    # Startup complete
    yield
    # Shutdown
    await close_redis()


app = FastAPI(
    title=f"{settings.app_name} — Agentic Operating System",
    description="Conversational, agentic ERP replacement for mid-market enterprises",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── Middleware (order matters: last added = first executed) ──

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

# ── Routes ──

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {
        "name": "AOS — Agentic Operating System",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }

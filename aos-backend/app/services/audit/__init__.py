"""Audit service — append-only log with hash-chain integrity."""
from app.services.audit.service import AuditService, AuditEventInput, compute_hash

__all__ = ["AuditService", "AuditEventInput", "compute_hash"]

"""
Append-only audit trail helpers.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import g, request

from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.audit")


def current_actor_id() -> str | None:
    user = getattr(g, "current_user", None) or {}
    return user.get("id") or user.get("user_id") or user.get("sub")


def current_actor_name() -> str | None:
    user = getattr(g, "current_user", None) or {}
    return user.get("username") or user.get("name") or user.get("email")


def write_audit(
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Best-effort audit writer. It must never break the user workflow."""
    payload = {
        "actor_id": current_actor_id(),
        "actor_name": current_actor_name(),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_data": before,
        "after_data": after,
        "metadata": metadata or {},
        "ip_address": request.headers.get("X-Forwarded-For", request.remote_addr),
        "user_agent": request.headers.get("User-Agent"),
    }
    try:
        sb = get_client()
        if not sb:
            return
        try:
            sb.table("audit_logs").insert(payload).execute()
        except Exception:
            sb.table("audit_trail").insert(payload).execute()
    except Exception as exc:
        logger.warning("Audit write skipped: %s", exc)


def record_audit(actor_id, actor_name, action, entity_type, entity_id=None, before=None, after=None, request=None):
    metadata = {}
    if request is not None:
        metadata = {
            "path": getattr(request, "path", None),
            "method": getattr(request, "method", None),
        }
    payload = {
        "actor_id": actor_id,
        "actor_name": actor_name,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_data": before,
        "after_data": after,
        "metadata": metadata,
        "ip_address": request.headers.get("X-Forwarded-For", request.remote_addr) if request else None,
        "user_agent": request.headers.get("User-Agent") if request else None,
    }
    try:
        sb = get_client()
        if sb:
            sb.table("audit_logs").insert({k: v for k, v in payload.items() if v is not None}).execute()
    except Exception as exc:
        logger.warning("Audit write skipped: %s", exc)

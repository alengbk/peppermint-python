from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Session
from app.models.models import AuditLog


def audit_log(
    session: Session,
    user_id: Optional[str],
    email: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    changes: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    detail: Optional[str] = None,
    source: str = "human",
):
    log = AuditLog(
        user_id=user_id,
        email=email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
        detail=detail,
        source=source,
    )
    session.add(log)
    session.commit()

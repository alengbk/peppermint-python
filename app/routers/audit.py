from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_session
from app.models.models import AuditLog, User
from app.auth import get_current_admin_user

router = APIRouter()


class AuditLogPublic(BaseModel):
    id: str
    createdAt: datetime
    userId: Optional[str] = None
    email: str
    action: str
    entityType: Optional[str] = None
    entityId: Optional[str] = None
    changes: Optional[dict] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    detail: Optional[str] = None
    source: str = "human"

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    logs: list
    total: int
    page: int
    pageSize: int


@router.get("/logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    source: Optional[str] = None,
    email: Optional[str] = None,
    success: Optional[bool] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if source:
        query = query.where(AuditLog.source == source)
    if email:
        query = query.where(AuditLog.email.contains(email))
    if from_date:
        try:
            d = datetime.fromisoformat(from_date)
            query = query.where(AuditLog.created_at >= d)
        except ValueError:
            pass
    if to_date:
        try:
            d = datetime.fromisoformat(to_date)
            query = query.where(AuditLog.created_at <= d)
        except ValueError:
            pass

    total = session.exec(select(func.count()).select_from(query.subquery())).first() or 0
    logs = session.exec(
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()

    return AuditLogListResponse(
        logs=[AuditLogPublic(
            id=log.id,
            createdAt=log.created_at,
            userId=log.user_id,
            email=log.email,
            action=log.action,
            entityType=log.entity_type,
            entityId=log.entity_id,
            changes=log.changes,
            ipAddress=log.ip_address,
            userAgent=log.user_agent,
            detail=log.detail,
            source=log.source,
        ) for log in logs],
        total=total,
        page=page,
        pageSize=pageSize,
    )

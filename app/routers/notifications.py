from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_session
from app.models.models import Notification, User
from app.auth import get_current_user

router = APIRouter()


class NotificationPublic(BaseModel):
    id: str
    read: bool
    text: str
    userId: str
    ticketId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


def map_notification(n: Notification) -> NotificationPublic:
    return NotificationPublic(
        id=n.id,
        read=n.read,
        text=n.text,
        userId=n.user_id,
        ticketId=n.ticket_id,
        createdAt=n.created_at,
        updatedAt=n.updated_at,
    )


@router.get("", response_model=List[NotificationPublic])
async def list_notifications(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.read == False)
    
    notifications = session.exec(
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return [map_notification(n) for n in notifications]


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    notification = session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    notification.read = True
    notification.updated_at = datetime.now(timezone.utc)
    session.add(notification)
    session.commit()
    return {"success": True}


@router.put("/read-all")
async def mark_all_read(
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    notifications = session.exec(
        select(Notification).where(Notification.user_id == current_user.id, Notification.read == False)
    ).all()
    for n in notifications:
        n.read = True
        n.updated_at = datetime.now(timezone.utc)
        session.add(n)
    session.commit()
    return {"success": True, "count": len(notifications)}
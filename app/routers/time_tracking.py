from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_session
from app.models.models import TimeTracking, Ticket, User, Client
from app.auth import get_current_user

router = APIRouter()


class TimeTrackingCreate(BaseModel):
    title: str
    comment: Optional[str] = None
    time: int
    ticketId: Optional[str] = None
    clientId: Optional[str] = None


class TimeTrackingUpdate(BaseModel):
    title: Optional[str] = None
    comment: Optional[str] = None
    time: Optional[int] = None


class TimeTrackingPublic(BaseModel):
    id: str
    title: str
    comment: Optional[str] = None
    time: int
    userId: Optional[str] = None
    clientId: Optional[str] = None
    ticketId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


def map_time(t: TimeTracking) -> TimeTrackingPublic:
    return TimeTrackingPublic(
        id=t.id,
        title=t.title,
        comment=t.comment,
        time=t.time,
        userId=t.user_id,
        clientId=t.client_id,
        ticketId=t.ticket_id,
        createdAt=t.created_at,
        updatedAt=t.updated_at,
    )


@router.post("", response_model=TimeTrackingPublic)
async def create_time_entry(
    time_data: TimeTrackingCreate,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    if time_data.ticketId:
        ticket = session.get(Ticket, time_data.ticketId)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
    
    if time_data.clientId:
        client = session.get(Client, time_data.clientId)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    
    entry = TimeTracking(
        title=time_data.title,
        comment=time_data.comment,
        time=time_data.time,
        user_id=current_user.id,
        ticket_id=time_data.ticketId,
        client_id=time_data.clientId,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return map_time(entry)


@router.get("", response_model=List[TimeTrackingPublic])
async def list_time_entries(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    ticketId: Optional[str] = None,
    userId: Optional[str] = None,
    clientId: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    query = select(TimeTracking)
    
    if ticketId:
        query = query.where(TimeTracking.ticket_id == ticketId)
    if userId:
        query = query.where(TimeTracking.user_id == userId)
    if clientId:
        query = query.where(TimeTracking.client_id == clientId)
    
    entries = session.exec(
        query.order_by(TimeTracking.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return [map_time(e) for e in entries]


@router.put("/{entry_id}", response_model=TimeTrackingPublic)
async def update_time_entry(
    entry_id: str,
    time_data: TimeTrackingUpdate,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    entry = session.get(TimeTracking, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    if entry.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    data = time_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(entry, key, value)
    
    entry.updated_at = datetime.now(timezone.utc)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return map_time(entry)


@router.delete("/{entry_id}")
async def delete_time_entry(
    entry_id: str,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    entry = session.get(TimeTracking, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    if entry.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    session.delete(entry)
    session.commit()
    return {"success": True}
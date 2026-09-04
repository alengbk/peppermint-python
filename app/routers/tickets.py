import csv
import io
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from app.database import get_session
from app.models.models import Ticket, TicketStatus, TicketType, Client, User, Team, Comment
from app.auth import get_current_user, get_current_admin_user, require_permission, get_auth_context, AuthContext
from app.audit import audit_log

router = APIRouter()


class TicketCreate(BaseModel):
    name: Optional[str] = None
    title: str
    detail: Optional[str] = None
    email: Optional[str] = None
    priority: Optional[str] = "low"
    type: Optional[str] = "support"
    company: Optional[Dict[str, Any]] = None
    engineer: Optional[Dict[str, Any]] = None
    createdBy: Optional[Dict[str, Any]] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    detail: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    type: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    note: Optional[str] = None
    userId: Optional[str] = None
    clientId: Optional[str] = None
    teamId: Optional[str] = None
    locked: Optional[bool] = None
    hidden: Optional[bool] = None
    isComplete: Optional[bool] = None


class TicketPublic(BaseModel):
    id: str
    number: int
    title: str
    detail: Optional[str] = None
    status: str
    priority: str
    type: str
    email: Optional[str] = None
    name: Optional[str] = None
    note: Optional[str] = None
    isComplete: bool
    locked: bool
    hidden: bool
    createdAt: datetime
    updatedAt: datetime
    createdBy: Optional[Dict[str, Any]] = None
    client: Optional[Dict[str, Any]] = None
    assignedTo: Optional[Dict[str, Any]] = None
    team: Optional[Dict[str, Any]] = None
    fromImap: bool = False
    dedupCount: int = 1
    lastSeenAt: Optional[datetime] = None
    dedupTimestamps: list = []

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    tickets: List[TicketPublic]
    total: int
    page: int
    pageSize: int


def map_ticket(ticket: Ticket) -> TicketPublic:
    return TicketPublic(
        id=ticket.id,
        number=ticket.number,
        title=ticket.title,
        detail=ticket.detail,
        status=ticket.status.value if isinstance(ticket.status, TicketStatus) else ticket.status,
        priority=ticket.priority,
        type=ticket.type.value if isinstance(ticket.type, TicketType) else ticket.type,
        email=ticket.email,
        name=ticket.name,
        note=ticket.note,
        isComplete=ticket.is_complete,
        locked=ticket.locked,
        hidden=ticket.hidden,
        createdAt=ticket.created_at,
        updatedAt=ticket.updated_at,
        createdBy=ticket.created_by,
        client={"id": ticket.client.id, "name": ticket.client.name, "email": ticket.client.email} if ticket.client else None,
        assignedTo={"id": ticket.assigned_to.id, "name": ticket.assigned_to.name, "email": ticket.assigned_to.email} if ticket.assigned_to else None,
        team={"id": ticket.team.id, "name": ticket.team.name} if ticket.team else None,
        fromImap=ticket.from_imap,
        dedupCount=ticket.dedup_count,
        lastSeenAt=ticket.last_seen_at,
        dedupTimestamps=ticket.dedup_timestamps or [],
    )


@router.post("", response_model=TicketPublic)
async def create_ticket(
    ticket_data: TicketCreate,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    return await _create_ticket_internal(ticket_data, session, ctx)


async def _create_ticket_internal(ticket_data, session: Session, ctx: AuthContext) -> TicketPublic:
    # Dedup: check for open ticket with same fingerprint
    fingerprint = hashlib.sha256(
        f"{ticket_data.title}|{ticket_data.detail}".encode()
    ).hexdigest()[:16]

    existing = session.exec(
        select(Ticket).where(
            Ticket.fingerprint == fingerprint,
            Ticket.status != TicketStatus.done,
        )
    ).first()

    if existing:
        existing.dedup_count += 1
        now = datetime.now(timezone.utc)
        existing.last_seen_at = now
        existing.dedup_timestamps = (existing.dedup_timestamps or []) + [now.isoformat()]
        existing.updated_at = now
        session.add(existing)
        session.commit()
        session.refresh(existing)
        audit_log(session, user_id=ctx.user_id, email=ctx.email,
                  action="ticket.dedup", entity_type="ticket", entity_id=existing.id,
                  detail=f"Dedup #{existing.number}: {existing.title} (count={existing.dedup_count})", source=ctx.source)
        return map_ticket(existing)

    # Get next ticket number
    max_number = session.exec(select(func.max(Ticket.number))).first() or 0
    next_number = max_number + 1

    # Parse client
    client = None
    if ticket_data.company and ticket_data.company.get("id"):
        client = session.get(Client, ticket_data.company["id"])

    # Parse assigned engineer
    assigned_to = None
    if ticket_data.engineer and ticket_data.engineer.get("id") and ticket_data.engineer.get("name") != "Unassigned":
        assigned_to = session.get(User, ticket_data.engineer["id"])

    # Parse createdBy
    created_by = ticket_data.createdBy or {
        "id": ctx.entity.id if ctx.source == "human" else ctx.email,
        "name": ctx.entity.name,
        "role": "api" if ctx.source == "api" else ("admin" if ctx.entity.is_admin else "agent"),
        "email": ctx.email,
    }

    now = datetime.now(timezone.utc)
    ticket = Ticket(
        number=next_number,
        name=ticket_data.name,
        title=ticket_data.title,
        detail=ticket_data.detail,
        email=ticket_data.email,
        priority=ticket_data.priority,
        type=TicketType(ticket_data.type.lower()) if ticket_data.type else TicketType.support,
        status=TicketStatus.needs_support,
        client=client,
        assigned_to=assigned_to,
        created_by=created_by,
        fingerprint=fingerprint,
        dedup_count=1,
        last_seen_at=now,
        dedup_timestamps=[now.isoformat()],
        from_imap=False,
        is_complete=False,
        locked=False,
        hidden=False,
        created_at=now,
        updated_at=now,
    )

    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    audit_log(session, user_id=ctx.user_id, email=ctx.email,
              action="ticket.create", entity_type="ticket", entity_id=ticket.id,
              detail=f"Ticket #{ticket.number}: {ticket.title}", source=ctx.source)
    return map_ticket(ticket)


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    userId: Optional[str] = None,
    clientId: Optional[str] = None,
    teamId: Optional[str] = None,
    hidden: Optional[bool] = False,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    query = select(Ticket)
    
    if hidden is False:
        query = query.where(Ticket.hidden == False)
    if status:
        try:
            query = query.where(Ticket.status == TicketStatus(status))
        except ValueError:
            pass
    if priority:
        query = query.where(Ticket.priority == priority)
    if type:
        try:
            query = query.where(Ticket.type == TicketType(type))
        except ValueError:
            pass
    if search:
        query = query.where(
            Ticket.title.contains(search) | 
            Ticket.detail.contains(search) |
            Ticket.name.contains(search)
        )
    if userId:
        query = query.where(Ticket.user_id == userId)
    if clientId:
        query = query.where(Ticket.client_id == clientId)
    if teamId:
        query = query.where(Ticket.team_id == teamId)

    total = session.exec(select(func.count()).select_from(query.subquery())).first() or 0
    
    tickets = session.exec(
        query.order_by(Ticket.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()

    return TicketListResponse(
        tickets=[map_ticket(t) for t in tickets],
        total=total,
        page=page,
        pageSize=pageSize,
    )


@router.get("/export/csv")
async def export_tickets_csv(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    userId: Optional[str] = None,
    clientId: Optional[str] = None,
    teamId: Optional[str] = None,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    query = select(Ticket)
    if status:
        try:
            query = query.where(Ticket.status == TicketStatus(status))
        except ValueError:
            pass
    if priority:
        query = query.where(Ticket.priority == priority)
    if type:
        try:
            query = query.where(Ticket.type == TicketType(type))
        except ValueError:
            pass
    if search:
        query = query.where(Ticket.title.contains(search) | Ticket.detail.contains(search) | Ticket.name.contains(search))
    if userId:
        query = query.where(Ticket.user_id == userId)
    if clientId:
        query = query.where(Ticket.client_id == clientId)
    if teamId:
        query = query.where(Ticket.team_id == teamId)
    tickets = session.exec(query.order_by(Ticket.created_at.desc())).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Number", "Title", "Status", "Priority", "Type", "Assignee Name", "Assignee Email", "Client", "Created At", "Updated At"])
    for t in tickets:
        writer.writerow([
            t.number,
            t.title,
            t.status.value if isinstance(t.status, TicketStatus) else t.status,
            t.priority,
            t.type.value if isinstance(t.type, TicketType) else t.type,
            t.assigned_to.name if t.assigned_to else "",
            t.assigned_to.email if t.assigned_to else "",
            t.client.name if t.client else "",
            t.created_at.isoformat(),
            t.updated_at.isoformat(),
        ])
    output.seek(0)
    audit_log(session, user_id=ctx.user_id, email=ctx.email,
              action="ticket.csv_export", detail=f"Exported {len(tickets)} tickets", source=ctx.source)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tickets.csv"})


@router.get("/{ticket_id}", response_model=TicketPublic)
async def get_ticket(
    ticket_id: str,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return map_ticket(ticket)


@router.put("/{ticket_id}", response_model=TicketPublic)
async def update_ticket(
    ticket_id: str,
    ticket_data: TicketUpdate,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    changes = {}
    data = ticket_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "status" and value:
            old = ticket.status.value if isinstance(ticket.status, TicketStatus) else ticket.status
            if value != old:
                changes["status"] = {"from": old, "to": value}
            try:
                ticket.status = TicketStatus(value)
            except ValueError:
                pass
        elif key == "type" and value:
            try:
                ticket.type = TicketType(value)
            except ValueError:
                pass
        elif key == "isComplete":
            ticket.is_complete = value
        elif key == "userId":
            old_id = ticket.user_id
            if value != old_id:
                old_name = ticket.assigned_to.name if ticket.assigned_to else "Unassigned"
                new_user = session.get(User, value) if value else None
                changes["assignee"] = {"from": old_name, "to": new_user.name if new_user else "Unassigned"}
            ticket.user_id = value
            ticket.assigned_to = session.get(User, value) if value else None
        elif key == "clientId":
            ticket.client_id = value
            ticket.client = session.get(Client, value) if value else None
        elif key == "teamId":
            ticket.team_id = value
            ticket.team = session.get(Team, value) if value else None
        elif hasattr(ticket, key):
            old_val = getattr(ticket, key)
            if value != old_val and key not in changes:
                changes[key] = {"from": old_val, "to": value}
            setattr(ticket, key, value)
    
    ticket.updated_at = datetime.now(timezone.utc)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    if changes.get("status") and changes["status"]["to"] == "done":
        audit_log(session, user_id=ctx.user_id, email=ctx.email,
                  action="ticket.close", entity_type="ticket", entity_id=ticket.id,
                  changes=changes, detail=f"Ticket #{ticket.number}: {ticket.title}", source=ctx.source)
    elif changes.get("assignee"):
        audit_log(session, user_id=ctx.user_id, email=ctx.email,
                  action="ticket.assign", entity_type="ticket", entity_id=ticket.id,
                  changes=changes, detail=f"Ticket #{ticket.number} → {changes['assignee']['to']}", source=ctx.source)
    elif changes:
        audit_log(session, user_id=ctx.user_id, email=ctx.email,
                  action="ticket.update", entity_type="ticket", entity_id=ticket.id,
                  changes=changes, detail=f"Ticket #{ticket.number}: {ticket.title}", source=ctx.source)
    return map_ticket(ticket)


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: str,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    if ctx.source == "human" and ctx.entity.is_admin:
        pass
    elif ctx.source == "api":
        raise HTTPException(status_code=403, detail="API keys cannot delete tickets")
    else:
        raise HTTPException(status_code=403, detail="Admin access required")
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    audit_log(session, user_id=ctx.user_id, email=ctx.email,
              action="ticket.delete", entity_type="ticket", entity_id=ticket_id,
              detail=f"Deleted ticket #{ticket.number}: {ticket.title}", source=ctx.source)
    session.delete(ticket)
    session.commit()
    return {"success": True}
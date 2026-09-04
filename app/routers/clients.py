from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_session
from app.models.models import Client
from app.auth import get_current_user, get_current_admin_user
from app.audit import audit_log

router = APIRouter()


class ClientCreate(BaseModel):
    name: str
    email: str
    contactName: str
    number: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    contactName: Optional[str] = None
    number: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class ClientPublic(BaseModel):
    id: str
    name: str
    email: str
    contactName: str
    number: Optional[str] = None
    notes: Optional[str] = None
    active: bool
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


def map_client(client: Client) -> ClientPublic:
    return ClientPublic(
        id=client.id,
        name=client.name,
        email=client.email,
        contactName=client.contact_name,
        number=client.number,
        notes=client.notes,
        active=client.active,
        createdAt=client.created_at,
        updatedAt=client.updated_at,
    )


@router.post("", response_model=ClientPublic)
async def create_client(
    client_data: ClientCreate,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    existing = session.exec(select(Client).where(Client.email == client_data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Client with this email already exists")
    
    client = Client(
        name=client_data.name,
        email=client_data.email,
        contact_name=client_data.contactName,
        number=client_data.number,
        notes=client_data.notes,
        active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(client)
    session.commit()
    session.refresh(client)
    audit_log(session, user_id=current_user.id if hasattr(current_user, 'id') else None,
              email=current_user.email if hasattr(current_user, 'email') else "system",
              action="client.create", entity_type="client", entity_id=client.id,
              detail=f"Created client {client.name} ({client.email})")
    return map_client(client)


@router.get("", response_model=List[ClientPublic])
async def list_clients(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    query = select(Client)
    if search:
        query = query.where(Client.name.contains(search) | Client.email.contains(search))
    if active is not None:
        query = query.where(Client.active == active)
    
    clients = session.exec(
        query.order_by(Client.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return [map_client(c) for c in clients]


@router.get("/{client_id}", response_model=ClientPublic)
async def get_client(
    client_id: str,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return map_client(client)


@router.put("/{client_id}", response_model=ClientPublic)
async def update_client(
    client_id: str,
    client_data: ClientUpdate,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    data = client_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "contactName":
            client.contact_name = value
        elif hasattr(client, key):
            setattr(client, key, value)
    
    client.updated_at = datetime.now(timezone.utc)
    session.add(client)
    session.commit()
    session.refresh(client)
    return map_client(client)


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user),
):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    audit_log(session, user_id=current_user.id, email=current_user.email,
              action="client.delete", entity_type="client", entity_id=client_id,
              detail=f"Deleted client {client.name} ({client.email})")
    session.delete(client)
    session.commit()
    return {"success": True}
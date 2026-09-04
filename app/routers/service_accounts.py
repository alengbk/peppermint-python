from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_session
from app.models.models import ServiceAccount, User
from app.auth import get_current_admin_user
from app.core.security import get_password_hash
from app.audit import audit_log
import secrets

router = APIRouter()


class ServiceAccountCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ServiceAccountResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    key_prefix: str
    active: bool
    last_used_at: Optional[datetime] = None
    created_by: str

    class Config:
        from_attributes = True


class ServiceAccountCreated(BaseModel):
    id: str
    name: str
    api_key: str
    description: Optional[str] = None


class ServiceAccountRegenerated(BaseModel):
    id: str
    name: str
    api_key: str


def _generate_api_key() -> tuple[str, str, str]:
    secret = secrets.token_hex(32)
    full_key = f"pep_{secret}"
    prefix = full_key[:20]
    hash_value = get_password_hash(full_key)
    return full_key, prefix, hash_value


@router.post("/service-account", response_model=ServiceAccountCreated, status_code=201)
async def create_service_account(
    data: ServiceAccountCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    existing = session.exec(select(ServiceAccount).where(ServiceAccount.name == data.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Service account name already exists")
    full_key, prefix, key_hash = _generate_api_key()
    sa = ServiceAccount(
        name=data.name,
        description=data.description,
        key_prefix=prefix,
        key_hash=key_hash,
        created_by=current_user.email,
    )
    session.add(sa)
    session.commit()
    session.refresh(sa)
    audit_log(session, user_id=current_user.id, email=current_user.email,
              action="service_account.create", entity_type="service_account", entity_id=sa.id,
              detail=f"Created service account {data.name}", source="human")
    return ServiceAccountCreated(id=sa.id, name=sa.name, api_key=full_key, description=sa.description)


@router.get("/service-account", response_model=list[ServiceAccountResponse])
async def list_service_accounts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    accounts = session.exec(select(ServiceAccount).order_by(ServiceAccount.name)).all()
    return accounts


@router.delete("/service-account/{sa_id}")
async def delete_service_account(
    sa_id: str,
    hard: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    sa = session.get(ServiceAccount, sa_id)
    if not sa:
        raise HTTPException(status_code=404, detail="Service account not found")
    if hard:
        name = sa.name
        session.delete(sa)
        audit_log(session, user_id=current_user.id, email=current_user.email,
                  action="service_account.delete", entity_type="service_account", entity_id=sa_id,
                  detail=f"Permanently deleted service account {name}", source="human")
        session.commit()
        return {"success": True, "message": "Service account permanently deleted"}
    sa.active = False
    session.add(sa)
    session.commit()
    audit_log(session, user_id=current_user.id, email=current_user.email,
              action="service_account.delete", entity_type="service_account", entity_id=sa_id,
              detail=f"Deactivated service account {sa.name}", source="human")
    return {"success": True, "message": "Service account deactivated"}


@router.post("/service-account/{sa_id}/regenerate", response_model=ServiceAccountRegenerated)
async def regenerate_api_key(
    sa_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    sa = session.get(ServiceAccount, sa_id)
    if not sa:
        raise HTTPException(status_code=404, detail="Service account not found")
    if not sa.active:
        raise HTTPException(status_code=400, detail="Cannot regenerate key for inactive account")
    full_key, prefix, key_hash = _generate_api_key()
    sa.key_prefix = prefix
    sa.key_hash = key_hash
    session.add(sa)
    session.commit()
    audit_log(session, user_id=current_user.id, email=current_user.email,
              action="service_account.regenerate", entity_type="service_account", entity_id=sa_id,
              detail=f"Regenerated API key for {sa.name}", source="human")
    return ServiceAccountRegenerated(id=sa.id, name=sa.name, api_key=full_key)

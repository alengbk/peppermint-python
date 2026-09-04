from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_session
from app.models.models import Config
from app.auth import get_current_user, get_current_admin_user
from app.audit import audit_log

router = APIRouter()


class ConfigUpdate(BaseModel):
    notifications: Optional[list] = None
    sso_provider: Optional[str] = None
    sso_active: Optional[bool] = None
    gh_version: Optional[str] = None
    client_version: Optional[str] = None
    feature_previews: Optional[bool] = None
    roles_active: Optional[bool] = None
    first_time_setup: Optional[bool] = None


class ConfigPublic(BaseModel):
    id: str
    notifications: Optional[list] = None
    sso_provider: Optional[str] = None
    sso_active: bool = False
    gh_version: Optional[str] = None
    client_version: Optional[str] = None
    feature_previews: bool = False
    roles_active: bool = False
    first_time_setup: bool = True

    class Config:
        from_attributes = True


def map_config(config: Config) -> ConfigPublic:
    return ConfigPublic(
        id=config.id,
        notifications=config.notifications,
        sso_provider=config.sso_provider,
        sso_active=config.sso_active,
        gh_version=config.gh_version,
        client_version=config.client_version,
        feature_previews=config.feature_previews,
        roles_active=config.roles_active,
        first_time_setup=config.first_time_setup,
    )


@router.get("", response_model=ConfigPublic)
async def get_config(
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    config = session.exec(select(Config)).first()
    if not config:
        config = Config(first_time_setup=True)
        session.add(config)
        session.commit()
        session.refresh(config)
    return map_config(config)


@router.put("", response_model=ConfigPublic)
async def update_config(
    config_data: ConfigUpdate,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user),
):
    config = session.exec(select(Config)).first()
    if not config:
        config = Config()
        session.add(config)
    
    data = config_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(config, key, value)
    
    config.updated_at = datetime.now(timezone.utc)
    session.add(config)
    session.commit()
    session.refresh(config)
    return map_config(config)


@router.post("/complete-setup")
async def complete_setup(
    session: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user),
):
    config = session.exec(select(Config)).first()
    if config:
        config.first_time_setup = False
        config.updated_at = datetime.now(timezone.utc)
        session.add(config)
        session.commit()
    audit_log(session, user_id=current_user.id, email=current_user.email,
              action="config.complete_setup", detail="First-time setup completed")
    return {"success": True}
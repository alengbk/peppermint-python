from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_session
from app.models.models import User
from app.auth import get_current_user, get_current_admin_user
from app.core.security import get_password_hash
from app.audit import audit_log

router = APIRouter()


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    admin: bool = False


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    is_admin: Optional[bool] = None
    language: Optional[str] = None
    image: Optional[str] = None
    password: Optional[str] = None


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    isAdmin: bool
    language: Optional[str] = None
    image: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


def map_user(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        name=user.name,
        email=user.email,
        isAdmin=user.is_admin,
        language=user.language,
        image=user.image,
        createdAt=user.created_at,
        updatedAt=user.updated_at,
    )


@router.post("", response_model=UserPublic)
async def create_user(
    user_data: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    existing_email = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_name = session.exec(select(User).where(User.name == user_data.name)).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Name already taken")
    
    user = User(
        email=user_data.email,
        name=user_data.name,
        password=get_password_hash(user_data.password),
        is_admin=user_data.admin,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    audit_log(session, user_id=current_user.id, email=current_user.email,
              action="user.create", entity_type="user", entity_id=user.id,
              detail=f"Created user {user.email} (admin={user.is_admin})")
    return map_user(user)


@router.get("", response_model=List[UserPublic])
async def list_users(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(User)
    if search:
        query = query.where(User.name.contains(search) | User.email.contains(search))
    
    users = session.exec(
        query.order_by(User.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return [map_user(u) for u in users]


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return map_user(user)


@router.put("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_data.name and user_data.name != user.name:
        dup = session.exec(select(User).where(User.name == user_data.name)).first()
        if dup:
            raise HTTPException(status_code=400, detail="Name already taken")

    data = user_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "password" and value:
            user.password = get_password_hash(value)
        elif key == "isAdmin":
            user.is_admin = value
        elif hasattr(user, key):
            setattr(user, key, value)
    
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)
    return map_user(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    audit_log(session, user_id=current_user.id, email=current_user.email,
              action="user.delete", entity_type="user", entity_id=user_id,
              detail=f"Deleted user {user.email}")
    session.delete(user)
    session.commit()
    return {"success": True}
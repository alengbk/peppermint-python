from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional

from app.database import get_session
from app.models.models import User, Config as ConfigModel
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.auth import get_current_user, get_current_user_optional
from app.audit import audit_log

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPublic"


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    admin: bool = False


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    is_admin: bool
    image: Optional[str] = None
    language: Optional[str] = "en"
    team_id: Optional[str] = None


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    user = session.exec(select(User).where(User.name == form_data.username)).first()
    if not user or not user.password or not verify_password(form_data.password, user.password):
        audit_log(session, user_id=None, email=form_data.username, action="auth.login_failed",
                  ip_address=ip, user_agent=ua, detail="Invalid username or password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.id})
    user_public = UserPublic(
        id=user.id,
        name=user.name,
        email=user.email,
        is_admin=user.is_admin,
        image=user.image,
        language=user.language,
        team_id=user.team_id,
    )
    audit_log(session, user_id=user.id, email=user.email, action="auth.login",
              ip_address=ip, user_agent=ua, detail="Login successful")
    return {"access_token": access_token, "token_type": "bearer", "user": user_public}


@router.post("/user/register", response_model=UserPublic)
async def register(
    request: Request,
    user_data: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_optional),
):
    # Check if first time setup - allow creating first admin without auth
    config = session.exec(select(ConfigModel)).first()
    is_first_setup = config and config.first_time_setup
    
    # Check if there are any users already
    existing_users = session.exec(select(User)).first()
    is_first_user = existing_users is None
    
    if not is_first_setup and not is_first_user:
        if not current_user or not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
    
    if is_first_setup and not user_data.admin:
        raise HTTPException(status_code=400, detail="First user must be admin")
    
    existing_email = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_name = session.exec(select(User).where(User.name == user_data.name)).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Name already taken")
    
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        password=hashed_password,
        name=user_data.name,
        is_admin=user_data.admin,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    admin_id = current_user.id if current_user else None
    audit_log(session, user_id=admin_id, email=current_user.email if current_user else user_data.email,
              action="auth.register", entity_type="user", entity_id=user.id,
              ip_address=request.client.host if request.client else None,
              detail=f"Registered user {user_data.email} (admin={user_data.admin})")
    return UserPublic(
        id=user.id,
        name=user.name,
        email=user.email,
        is_admin=user.is_admin,
        image=user.image,
        language=user.language,
        team_id=user.team_id,
    )


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserPublic(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        is_admin=current_user.is_admin,
        image=current_user.image,
        language=current_user.language,
        team_id=current_user.team_id,
    )


@router.post("/logout")
async def logout():
    return {"success": True, "message": "Logged out"}


@router.put("/language")
async def update_language(
    body: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    lang = body.get("language", "en")
    if lang not in ("en", "zh"):
        raise HTTPException(status_code=400, detail="Invalid language")
    user = session.get(User, current_user.id)
    user.language = lang
    session.add(user)
    session.commit()
    return {"language": lang}


@router.get("/check-first-setup")
async def check_first_setup(session: Session = Depends(get_session)):
    config = session.exec(select(ConfigModel)).first()
    return {"firstTimeSetup": config.first_time_setup if config else True}
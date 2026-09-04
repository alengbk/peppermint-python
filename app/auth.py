from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from dataclasses import dataclass
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.database import get_session
from app.models.models import User, Session as SessionModel, ServiceAccount
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token


@dataclass
class AuthContext:
    entity: Union[User, ServiceAccount]
    source: str  # "human" | "api"
    email: str
    user_id: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


def get_current_user_from_cookie(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = request.cookies.get("token")
    if not token:
        raise credentials_exception
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Optional[User]:
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    return session.get(User, user_id)


def require_permission(permission: str):
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if user.is_admin:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission} required",
        )
    return permission_checker


def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def get_current_admin_user_from_cookie(
    user: User = Depends(get_current_user_from_cookie),
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def get_current_api_key(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> ServiceAccount:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token or not token.startswith("pep_"):
        raise credentials_exception
    prefix = token[:20]
    sa = session.exec(
        select(ServiceAccount).where(
            ServiceAccount.key_prefix == prefix,
            ServiceAccount.active == True,
        )
    ).first()
    if not sa or not verify_password(token, sa.key_hash):
        raise credentials_exception
    sa.last_used_at = datetime.now(timezone.utc)
    session.add(sa)
    session.commit()
    return sa


def get_auth_context(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> AuthContext:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    if token.startswith("pep_"):
        prefix = token[:20]
        sa = session.exec(
            select(ServiceAccount).where(
                ServiceAccount.key_prefix == prefix,
                ServiceAccount.active == True,
            )
        ).first()
        if not sa or not verify_password(token, sa.key_hash):
            raise credentials_exception
        sa.last_used_at = datetime.now(timezone.utc)
        session.add(sa)
        session.commit()
        return AuthContext(entity=sa, source="api", email=sa.name, user_id=None)
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return AuthContext(entity=user, source="human", email=user.email, user_id=user.id)
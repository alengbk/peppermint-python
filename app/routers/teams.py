from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_session
from app.models.models import Team, User
from app.auth import get_current_user, get_current_admin_user

router = APIRouter()


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: Optional[str] = None


class TeamPublic(BaseModel):
    id: str
    name: str
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


def map_team(team: Team) -> TeamPublic:
    return TeamPublic(
        id=team.id,
        name=team.name,
        createdAt=team.created_at,
        updatedAt=team.updated_at,
    )


@router.post("", response_model=TeamPublic)
async def create_team(
    team_data: TeamCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    team = Team(
        name=team_data.name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(team)
    session.commit()
    session.refresh(team)
    return map_team(team)


@router.get("", response_model=List[TeamPublic])
async def list_teams(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    teams = session.exec(
        select(Team)
        .order_by(Team.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return [map_team(t) for t in teams]


@router.get("/{team_id}", response_model=TeamPublic)
async def get_team(
    team_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return map_team(team)


@router.put("/{team_id}", response_model=TeamPublic)
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    data = team_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(team, key, value)
    
    team.updated_at = datetime.now(timezone.utc)
    session.add(team)
    session.commit()
    session.refresh(team)
    return map_team(team)


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team)
    session.commit()
    return {"success": True}
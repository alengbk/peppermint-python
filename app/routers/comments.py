from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_session
from app.models.models import Comment, Ticket, User
from app.auth import get_auth_context, AuthContext
from app.audit import audit_log

router = APIRouter()


class CommentCreate(BaseModel):
    text: str
    public: bool = False
    reply: bool = False
    replyEmail: Optional[str] = None


class CommentUpdate(BaseModel):
    text: Optional[str] = None
    public: Optional[bool] = None


class CommentPublic(BaseModel):
    id: str
    text: str
    public: bool
    reply: bool
    replyEmail: Optional[str] = None
    edited: bool
    editedAt: Optional[datetime] = None
    previous: Optional[str] = None
    user: Optional[dict] = None
    ticketId: str
    createdAt: datetime

    class Config:
        from_attributes = True


def map_comment(c: Comment) -> CommentPublic:
    return CommentPublic(
        id=c.id,
        text=c.text,
        public=c.public,
        reply=c.reply,
        replyEmail=c.reply_email,
        edited=c.edited,
        editedAt=c.edited_at,
        previous=c.previous,
        user={"id": c.user.id, "name": c.user.name, "email": c.user.email} if c.user else None,
        ticketId=c.ticket_id,
        createdAt=c.created_at,
    )


@router.post("/{ticket_id}", response_model=CommentPublic)
async def create_comment(
    ticket_id: str,
    comment_data: CommentCreate,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    comment = Comment(
        text=comment_data.text,
        public=comment_data.public,
        reply=comment_data.reply,
        reply_email=comment_data.replyEmail,
        user_id=ctx.user_id,
        ticket_id=ticket_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    audit_log(session, user_id=ctx.user_id, email=ctx.email,
              action="comment.create", entity_type="comment", entity_id=comment.id,
              detail=f"Comment on ticket {ticket_id}", source=ctx.source)
    return map_comment(comment)


@router.get("/{ticket_id}", response_model=List[CommentPublic])
async def list_comments(
    ticket_id: str,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    comments = session.exec(
        select(Comment).where(Comment.ticket_id == ticket_id).order_by(Comment.created_at)
    ).all()
    return [map_comment(c) for c in comments]


@router.put("/{comment_id}", response_model=CommentPublic)
async def update_comment(
    comment_id: str,
    comment_data: CommentUpdate,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    comment = session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if ctx.source == "api":
        raise HTTPException(status_code=403, detail="API keys cannot update comments")
    
    if comment.user_id != ctx.user_id and not ctx.entity.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    data = comment_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "text" and value != comment.text:
            comment.previous = comment.text
            comment.edited = True
            comment.edited_at = datetime.now(timezone.utc)
        if key == "replyEmail":
            comment.reply_email = value
        else:
            setattr(comment, key, value)
    
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return map_comment(comment)


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: str,
    session: Session = Depends(get_session),
    ctx: AuthContext = Depends(get_auth_context),
):
    comment = session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if ctx.source == "api":
        raise HTTPException(status_code=403, detail="API keys cannot delete comments")
    
    if comment.user_id != ctx.user_id and not ctx.entity.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    audit_log(session, user_id=ctx.user_id, email=ctx.email,
              action="comment.delete", entity_type="comment", entity_id=comment_id,
              detail=f"Deleted comment on ticket {comment.ticket_id}", source=ctx.source)
    session.delete(comment)
    session.commit()
    return {"success": True}
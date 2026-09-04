import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import Enum as SQLEnum

if TYPE_CHECKING:
    from .models import User, Ticket, Client, Team, Comment, TimeTracking, Notification, Role, UserFile, TicketFile, Notes, Todos, Webhooks, KnowledgeBase, EmailQueue, ImapEmail, Discord, Slack, Email, Config, Uptime, EmailTemplate, UserRole


class UserRole(SQLModel, table=True):
    __tablename__ = "UserRole"
    user_id: str = Field(foreign_key="User.id", primary_key=True)
    role_id: str = Field(foreign_key="Role.id", primary_key=True)


class TicketStatus(str, enum.Enum):
    hold = "hold"
    needs_support = "needs_support"
    in_progress = "in_progress"
    in_review = "in_review"
    done = "done"


class TicketType(str, enum.Enum):
    bug = "bug"
    feature = "feature"
    support = "support"
    incident = "incident"
    service = "service"
    maintenance = "maintenance"
    access = "access"
    feedback = "feedback"


class HookType(str, enum.Enum):
    ticket_created = "ticket_created"
    ticket_status_changed = "ticket_status_changed"


class TemplateType(str, enum.Enum):
    ticket_created = "ticket_created"
    ticket_status_changed = "ticket_status_changed"
    ticket_assigned = "ticket_assigned"
    ticket_comment = "ticket_comment"


class User(SQLModel, table=True):
    __tablename__ = "User"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str = Field(unique=True, index=True)
    password: Optional[str] = None
    email: str = Field(unique=True, index=True)
    image: Optional[str] = None
    email_verified: Optional[bool] = None
    is_admin: bool = Field(default=False)
    language: Optional[str] = Field(default="en")
    notify_ticket_created: bool = Field(default=True)
    notify_ticket_status_changed: bool = Field(default=True)
    notify_ticket_comments: bool = Field(default=True)
    notify_ticket_assigned: bool = Field(default=True)
    first_login: bool = Field(default=True)
    external_user: bool = Field(default=False)
    out_of_office: bool = Field(default=False)
    out_of_office_message: Optional[str] = None
    out_of_office_start: Optional[datetime] = None
    out_of_office_end: Optional[datetime] = None

    team_id: Optional[str] = Field(default=None, foreign_key="Team.id")
    team: Optional["Team"] = Relationship(back_populates="members")

    tickets: List["Ticket"] = Relationship(back_populates="assigned_to", sa_relationship_kwargs={"foreign_keys": "Ticket.user_id"})
    created_tickets: List["Ticket"] = Relationship(back_populates="created_by_user", sa_relationship_kwargs={"foreign_keys": "Ticket.created_by_user_id"})
    comments: List["Comment"] = Relationship(back_populates="user")
    sessions: List["Session"] = Relationship(back_populates="user")
    time_tracking: List["TimeTracking"] = Relationship(back_populates="user")
    notifications: List["Notification"] = Relationship(back_populates="user")
    user_files: List["UserFile"] = Relationship(back_populates="user")
    ticket_files: List["TicketFile"] = Relationship(back_populates="user")
    notes: List["Notes"] = Relationship(back_populates="user")
    todos: List["Todos"] = Relationship(back_populates="user")
    roles: List["Role"] = Relationship(back_populates="users", link_model=UserRole)


class Role(SQLModel, table=True):
    __tablename__ = "Role"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    permissions: list = Field(default=[], sa_column=Column(JSON))
    is_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    users: List["User"] = Relationship(back_populates="roles", link_model=UserRole)


class Team(SQLModel, table=True):
    __tablename__ = "Team"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str

    members: List["User"] = Relationship(back_populates="team")
    tickets: List["Ticket"] = Relationship(back_populates="team")


class Ticket(SQLModel, table=True):
    __tablename__ = "Ticket"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: Optional[str] = None
    title: str
    detail: Optional[str] = None
    email: Optional[str] = None
    note: Optional[str] = None
    is_complete: bool = Field(default=False)
    priority: str = Field(default="low")
    linked: Optional[list] = Field(default=None, sa_column=Column(JSON))
    from_imap: bool = Field(default=False)
    number: int = Field(default=0)
    status: TicketStatus = Field(default=TicketStatus.needs_support, sa_column=Column(SQLEnum(TicketStatus)))
    type: TicketType = Field(default=TicketType.support, sa_column=Column(SQLEnum(TicketType)))
    hidden: bool = Field(default=False)
    created_by: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    locked: bool = Field(default=False)
    following: Optional[list] = Field(default=None, sa_column=Column(JSON))

    fingerprint: Optional[str] = Field(default=None, index=True)
    dedup_count: int = Field(default=1)
    last_seen_at: Optional[datetime] = None
    dedup_timestamps: list = Field(default=[], sa_column=Column(JSON))

    team_id: Optional[str] = Field(default=None, foreign_key="Team.id")
    team: Optional["Team"] = Relationship(back_populates="tickets")

    user_id: Optional[str] = Field(default=None, foreign_key="User.id")
    assigned_to: Optional["User"] = Relationship(back_populates="tickets", sa_relationship_kwargs={"foreign_keys": "Ticket.user_id"})

    client_id: Optional[str] = Field(default=None, foreign_key="Client.id")
    client: Optional["Client"] = Relationship(back_populates="tickets")

    created_by_user_id: Optional[str] = Field(default=None, foreign_key="User.id")
    created_by_user: Optional["User"] = Relationship(back_populates="created_tickets", sa_relationship_kwargs={"foreign_keys": "Ticket.created_by_user_id"})

    comments: List["Comment"] = Relationship(back_populates="ticket", sa_relationship_kwargs={"passive_deletes": True})
    time_tracking: List["TimeTracking"] = Relationship(back_populates="ticket")
    ticket_files: List["TicketFile"] = Relationship(back_populates="ticket")
    knowledge_base_links: List["KnowledgeBase"] = Relationship(back_populates="ticket")
    notifications: List["Notification"] = Relationship(back_populates="ticket")


class Client(SQLModel, table=True):
    __tablename__ = "Client"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    email: str = Field(unique=True, index=True)
    contact_name: str
    number: Optional[str] = None
    notes: Optional[str] = None
    active: bool = Field(default=True)

    tickets: List["Ticket"] = Relationship(back_populates="client")
    time_tracking: List["TimeTracking"] = Relationship(back_populates="client")


class Comment(SQLModel, table=True):
    __tablename__ = "Comment"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    text: str
    public: bool = Field(default=False)
    reply: bool = Field(default=False)
    reply_email: Optional[str] = None
    edited: bool = Field(default=False)
    edited_at: Optional[datetime] = None
    previous: Optional[str] = None

    user_id: Optional[str] = Field(default=None, foreign_key="User.id")
    user: Optional["User"] = Relationship(back_populates="comments")

    ticket_id: str = Field(foreign_key="Ticket.id", ondelete="CASCADE")
    ticket: "Ticket" = Relationship(back_populates="comments")


class TimeTracking(SQLModel, table=True):
    __tablename__ = "TimeTracking"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str
    comment: Optional[str] = None
    time: int

    user_id: Optional[str] = Field(default=None, foreign_key="User.id")
    user: Optional["User"] = Relationship(back_populates="time_tracking")

    client_id: Optional[str] = Field(default=None, foreign_key="Client.id")
    client: Optional["Client"] = Relationship(back_populates="time_tracking")

    ticket_id: Optional[str] = Field(default=None, foreign_key="Ticket.id")
    ticket: Optional["Ticket"] = Relationship(back_populates="time_tracking")


class Session(SQLModel, table=True):
    __tablename__ = "Session"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_token: str = Field(unique=True, index=True)
    user_id: str = Field(foreign_key="User.id", ondelete="CASCADE")
    expires: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    api_key: bool = Field(default=False)

    user: "User" = Relationship(back_populates="sessions")


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read: bool = Field(default=False)
    text: str

    user_id: str = Field(foreign_key="User.id")
    user: "User" = Relationship(back_populates="notifications")

    ticket_id: Optional[str] = Field(default=None, foreign_key="Ticket.id")
    ticket: Optional["Ticket"] = Relationship(back_populates="notifications")


class UserFile(SQLModel, table=True):
    __tablename__ = "UserFile"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filename: str
    path: str

    user_id: str = Field(foreign_key="User.id")
    user: "User" = Relationship(back_populates="user_files")


class TicketFile(SQLModel, table=True):
    __tablename__ = "TicketFile"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filename: str
    path: str
    mime: str
    encoding: str
    size: int

    ticket_id: str = Field(foreign_key="Ticket.id")
    ticket: "Ticket" = Relationship(back_populates="ticket_files")
    user_id: str = Field(foreign_key="User.id")
    user: "User" = Relationship(back_populates="ticket_files")


class Notes(SQLModel, table=True):
    __tablename__ = "Notes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str
    note: str
    favourited: bool = Field(default=False)

    user_id: str = Field(foreign_key="User.id")
    user: "User" = Relationship(back_populates="notes")


class Todos(SQLModel, table=True):
    __tablename__ = "Todos"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    text: str
    done: bool = Field(default=False)

    user_id: str = Field(foreign_key="User.id")
    user: "User" = Relationship(back_populates="todos")


class Webhooks(SQLModel, table=True):
    __tablename__ = "Webhooks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    url: str
    type: HookType = Field(sa_column=Column(SQLEnum(HookType)))
    active: bool
    secret: Optional[str] = None
    created_by: str


class Discord(SQLModel, table=True):
    __tablename__ = "Discord"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    secret: Optional[str] = None
    url: str
    active: bool = Field(default=False)


class Slack(SQLModel, table=True):
    __tablename__ = "Slack"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    secret: Optional[str] = None
    url: str
    active: bool = Field(default=False)


class Email(SQLModel, table=True):
    __tablename__ = "Email"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = Field(default=False)
    user: str
    pass_: Optional[str] = Field(default=None, alias="pass")
    secure: bool = Field(default=False)
    host: str
    reply: str
    port: str
    service_type: str = Field(default="other")
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    redirect_uri: Optional[str] = None


class Config(SQLModel, table=True):
    __tablename__ = "Config"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notifications: Optional[list] = Field(default=None, sa_column=Column(JSON))
    sso_provider: Optional[str] = None
    sso_active: bool = Field(default=False)
    gh_version: Optional[str] = None
    client_version: Optional[str] = None
    feature_previews: bool = Field(default=False)
    roles_active: bool = Field(default=False)
    encryption_key: Optional[bytes] = None
    first_time_setup: bool = Field(default=True)


class Uptime(SQLModel, table=True):
    __tablename__ = "Uptime"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    url: str
    active: bool = Field(default=False)
    webhook: Optional[str] = None
    latency: Optional[int] = None
    status: Optional[bool] = None


class KnowledgeBase(SQLModel, table=True):
    __tablename__ = "knowledgeBase"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str
    content: str
    tags: list = Field(default=[], sa_column=Column(JSON))
    author: str
    public: bool = Field(default=False)

    ticket_id: Optional[str] = Field(default=None, foreign_key="Ticket.id")
    ticket: Optional["Ticket"] = Relationship(back_populates="knowledge_base_links")


class EmailQueue(SQLModel, table=True):
    __tablename__ = "EmailQueue"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    username: str
    password: Optional[str] = None
    hostname: str
    tls: bool = Field(default=True)
    active: bool = Field(default=True)
    teams: Optional[list] = Field(default=None, sa_column=Column(JSON))
    service_type: str = Field(default="other")
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    redirect_uri: Optional[str] = None

    imap_emails: List["ImapEmail"] = Relationship(back_populates="email_queue")


class ImapEmail(SQLModel, table=True):
    __tablename__ = "Imap_Email"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    from_: Optional[str] = Field(default=None, alias="from")
    subject: Optional[str] = None
    body: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None

    email_queue_id: Optional[str] = Field(default=None, foreign_key="EmailQueue.id")
    email_queue: Optional["EmailQueue"] = Relationship(back_populates="imap_emails")


class EmailTemplate(SQLModel, table=True):
    __tablename__ = "emailTemplate"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    html: str
    type: TemplateType = Field(sa_column=Column(SQLEnum(TemplateType)))


class OAuthProvider(SQLModel, table=True):
    __tablename__ = "OAuthProvider"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    user_info_url: str
    redirect_uri: str
    scope: str


class SAMLProvider(SQLModel, table=True):
    __tablename__ = "SAMLProvider"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    entry_point: str
    issuer: str
    cert: str
    sso_login_url: str
    sso_logout_url: str
    audience: str
    recipient: str
    destination: str
    acs_url: str


class OpenIdConfig(SQLModel, table=True):
    __tablename__ = "openIdConfig"

    id: int = Field(default=None, primary_key=True)
    client_id: str
    issuer: str
    redirect_uri: str


class ServiceAccount(SQLModel, table=True):
    __tablename__ = "ServiceAccount"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    key_prefix: str = Field(unique=True, index=True)
    key_hash: str
    active: bool = Field(default=True)
    last_used_at: Optional[datetime] = None
    created_by: str


class AuditLog(SQLModel, table=True):
    __tablename__ = "AuditLog"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    email: str = ""
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    changes: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    detail: Optional[str] = None
    source: str = "human"


# Pydantic schemas for API
class TicketCreate(SQLModel):
    name: Optional[str] = None
    title: str
    detail: Optional[str] = None
    email: Optional[str] = None
    priority: Optional[str] = "low"
    type: Optional[str] = "support"
    company: Optional[dict] = None
    engineer: Optional[dict] = None
    createdBy: Optional[dict] = None


class TicketCreatePublic(SQLModel):
    name: Optional[str] = None
    title: str
    detail: Optional[str] = None
    email: Optional[str] = None
    priority: Optional[str] = "low"
    type: Optional[str] = "support"
    company: Optional[dict] = None
    engineer: Optional[dict] = None
    createdBy: Optional[dict] = None


class TicketResponse(SQLModel):
    id: str
    title: str
    detail: Optional[str] = None
    status: str
    priority: str
    type: str
    email: Optional[str] = None
    number: int
    createdAt: datetime
    updatedAt: datetime
    client: Optional[dict] = None
    assignedTo: Optional[dict] = None

    class Config:
        from_attributes = True


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserLogin(SQLModel):
    email: str
    password: str


class UserRegister(SQLModel):
    email: str
    password: str
    name: str
    admin: bool = False
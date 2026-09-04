from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.database import create_db_and_tables, engine
from app.routers import auth, tickets, users, clients, teams, comments, time_tracking, config, notifications, frontend, audit, service_accounts
from app.models.models import Config as ConfigModel
from app.database import get_session
from sqlmodel import Session, select


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # Initialize config if not exists
    from app.database import engine
    with Session(engine) as session:
        config = session.exec(select(ConfigModel)).first()
        if not config:
            config = ConfigModel(first_time_setup=True)
            session.add(config)
            session.commit()
    yield


app = FastAPI(
    title="Peppermint API",
    description="Peppermint Helpdesk/Ticketing System API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(frontend.router, tags=["frontend"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tickets.router, prefix="/api/v1/ticket", tags=["tickets"])
app.include_router(users.router, prefix="/api/v1/user", tags=["users"])
app.include_router(clients.router, prefix="/api/v1/client", tags=["clients"])
app.include_router(teams.router, prefix="/api/v1/team", tags=["teams"])
app.include_router(comments.router, prefix="/api/v1/comment", tags=["comments"])
app.include_router(time_tracking.router, prefix="/api/v1/time", tags=["time-tracking"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
app.include_router(service_accounts.router, prefix="/api/v1", tags=["service-accounts"])


@app.get("/")
async def root():
    return {"healthy": True, "service": "peppermint-api"}


@app.get("/api/v1/health")
async def health():
    return {"healthy": True}
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models.models import User
from app.auth import get_current_user_from_cookie, get_current_user_optional, get_current_admin_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _context(request: Request, user: User, title: str, active: str):
    return {
        "request": request,
        "title": title,
        "active": active,
        "user_name": user.name if user else "",
        "is_admin": user.is_admin if user else False,
    }


@router.get("/")
async def root():
    return RedirectResponse(url="/login", status_code=302)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie),
):
    return templates.TemplateResponse("dashboard.html", _context(request, current_user, "Dashboard", "dashboard"))


@router.get("/tickets", response_class=HTMLResponse)
async def tickets_page(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie),
):
    return templates.TemplateResponse("tickets.html", _context(request, current_user, "Tickets", "tickets"))


@router.get("/ticket/{ticket_id}", response_class=HTMLResponse)
async def ticket_detail_page(
    request: Request,
    ticket_id: str,
    current_user: User = Depends(get_current_user_from_cookie),
    session: Session = Depends(get_session),
):
    users = session.exec(select(User).order_by(User.name)).all()
    ctx = _context(request, current_user, "Ticket Detail", "tickets")
    ctx["ticket_id"] = ticket_id
    ctx["users"] = users
    return templates.TemplateResponse("ticket_detail.html", ctx)


@router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie),
):
    ctx = _context(request, current_user, "Users", "users")
    return templates.TemplateResponse("users.html", ctx)


@router.get("/clients", response_class=HTMLResponse)
async def clients_page(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie),
):
    ctx = _context(request, current_user, "Clients", "clients")
    return templates.TemplateResponse("clients.html", ctx)


@router.get("/audit", response_class=HTMLResponse)
async def audit_page(
    request: Request,
    current_user: User = Depends(get_current_admin_user_from_cookie),
):
    ctx = _context(request, current_user, "Audit Log", "audit")
    return templates.TemplateResponse("audit.html", ctx)


@router.get("/service-accounts", response_class=HTMLResponse)
async def service_accounts_page(
    request: Request,
    current_user: User = Depends(get_current_admin_user_from_cookie),
):
    ctx = _context(request, current_user, "Service Accounts", "service-accounts")
    return templates.TemplateResponse("service_accounts.html", ctx)

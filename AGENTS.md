# Peppermint-fork Python — Agent Guide

## Project Overview

Python FastAPI + SQLite rewrite of Peppermint helpdesk/ticketing system (original: Node.js/TypeScript/PostgreSQL).

## Tech Stack

- **Framework**: FastAPI + SQLModel (SQLAlchemy ORM)
- **Database**: SQLite (WAL mode, FK enabled, no external DB needed)
- **Auth**: JWT (python-jose) + PBKDF2-SHA256 self-implemented password hashing
- **Permissions**: RBAC (admin/agent)

## Directory Structure

```
app/
├── audit.py             # Audit log helper (audit_log())
├── auth.py              # Auth dependencies (get_current_user, require_permission, etc.)
├── database.py          # Engine, session, table creation (PRAGMA foreign_keys=ON)
├── main.py              # FastAPI app, lifespan, router registration
├── core/
│   ├── config.py        # Pydantic Settings (SECRET_KEY, DATABASE_URL, etc.)
│   ├── database.py      # (reserved)
│   └── security.py      # Password hashing & JWT token helpers
├── models/
│   └── models.py        # All SQLModel tables + inline Pydantic schemas
├── routers/
│   ├── auth.py          # login (by name), register, me, logout, check-first-setup
│   ├── tickets.py       # CRUD + CSV export (delete requires admin)
│   ├── users.py         # CRUD (name unique, admin-only delete)
│   ├── clients.py       # CRUD
│   ├── teams.py         # CRUD
│   ├── comments.py      # CRUD
│   ├── time_tracking.py # CRUD
│   ├── config.py        # get/update/complete-setup
│   ├── notifications.py # list/mark-read/mark-all-read
│   ├── frontend.py      # HTML page routes (login, dashboard, tickets, etc.)
│   ├── audit.py         # Audit log query API (admin)
│   └── service_accounts.py # API Key CRUD (admin)
├── templates/           # Jinja2 HTML templates
│   ├── base.html        # Layout: sidebar + header + content ("Peppermint-fork")
│   ├── login.html       # Username login, "Peppermint-fork" branding
│   ├── dashboard.html   # Stats cards + recent tickets
│   ├── tickets.html     # Filterable ticket list + create modal
│   ├── ticket_detail.html # Ticket detail + comments + sidebar fields + admin Delete btn
│   ├── users.html       # Admin: user list (create/edit/delete modal, name unique)
│   ├── clients.html     # Admin: client list (create/edit/delete modal)
│   ├── audit.html       # Admin: audit log viewer (source filter)
│   └── service_accounts.html # Admin: API key management
├── static/              # Static assets (served at /static)
│   ├── style.css        # All styles + modal display:flex rules
│   └── app.js           # Frontend JS: api() with safe JSON parsing
├── schemas/             # Future: dedicated Pydantic models
└── services/            # Future: business logic layer
create_via_api.py        # Minimal Python script: batch-create tickets via API Key
http_post_sample.py      # CLI tool for external machines to POST tickets via API Key
init.py                  # DB reset + admin creation (password: 1qaz+2wsx)
seed_tickets.py          # Random test ticket generator
test_api.py              # Full integration test suite
simple_test.py           # Quick smoke test
test_e2e.py              # E2E: register → login → ticket → close → CSV
test_audit.py            # E2E: verify all audit log action types
```

## Frontend

- **Templates**: Jinja2 (FastAPI built-in), rendered by `app/routers/frontend.py`
- **Auth flow**: Login form (username + password) → JWT stored in localStorage → Bearer header on API calls
- **All pages require auth** (except `/login` which redirects if already logged in)
- **Root `/`** redirects to `/login` (302)
- **JS**: Vanilla JS with `fetch()` API, no framework
- **CSS**: Single `style.css`, green-accent design
- **Modals**: All modals use `.hidden { display:none !important }` + `#modal-id { display:flex }` CSS, with `overflow-y:auto`
- **Error handling**: `api()` catches non-JSON responses and shows `Server error (N)` instead of JSON parse crash
- **Audit page**: `/audit` (admin only) — filterable audit log viewer with human/api source column, paginated (prev/next, page info, page size selector 50/100/200)
- **Service Accounts page**: `/service-accounts` (admin only) — API key management
- **Delete ticket**: Button in ticket detail topbar, admin-only (template-level `{% if is_admin %}`)
- **Language switching**: EN/中 toggle in sidebar footer, `PUT /api/v1/auth/language` endpoint, preference stored in `localStorage` + `User.language` (DB), `setLang()`/`applyLang()` in app.js, `data-en`/`data-zh` on translatable text + `data-placeholder-en`/`data-placeholder-zh` for placeholders, `__()` helper for JS dynamic strings
- **Translated pages**: All 9 templates fully translated; `app.js` badge helpers (`statusBadge`, `priorityBadge`, `typeBadge`) and all dynamic JS strings use `__()`
- **Source badge**: Tickets created via JWT show `Human` badge; via API key show `API` badge (check `createdBy.role` in ticket response)
- **Dedup display**: List/dashboard shows `×N` badge on title; detail sidebar shows Alert Count card with big number, last seen time, and full timeline of each repetition (`dedup_timestamps[]`)

## CSV Export

`GET /api/v1/ticket/export/csv` — accepts same filter params as ticket list, returns `tickets.csv` with BOM for Excel compatibility.

## Code Conventions

- All schemas (Pydantic models) are defined inline in each router file, not in `schemas/`
- All business logic is in routers, not in `services/` (future refactor target)
- Always use `from app.auth import get_current_user, ...` (single source of truth)
- Do NOT use `from app.routers.auth import ...`
- Auth functions are sync (not async) — FastAPI handles thread pool wrapping
- Email field uses `str` (not `EmailStr`) — strict email validation removed for flexibility
- New models: add to `app/models/models.py`
- New routers: register in `app/main.py` with prefix + tags
- Always call `audit_log()` when modifying data (create, update, delete)

## Auth System

- **Login by `name` (username)**, not email
- `User.name` is `unique=True, index=True`
- `User.email` remains required but no strict format validation
- `get_current_user` — requires valid JWT via Authorization header (API routes), raises 401 if missing/invalid
- `get_current_user_from_cookie` — requires valid JWT via `token` cookie (frontend page routes)
- `get_current_user_optional` — returns None if no token (for first-time setup)
- `get_current_admin_user` — requires admin role via Authorization header
- `get_current_admin_user_from_cookie` — requires admin role via `token` cookie (frontend admin pages)
- `get_current_api_key` — validates `Authorization: Bearer pep_<key>` against `ServiceAccount` table, raises 401 if invalid
- `get_auth_context` — accepts JWT or API key, returns `AuthContext` (entity, source="human"|"api", email, user_id)
- `require_permission(name)` — factory that checks admin role (simple RBAC)
- Public endpoints do NOT exist — all create/update/delete require auth
- Frontend uses cookie auth because browser navigation does not send custom headers

## Audit Log

All destructive/modification operations log to `AuditLog` table via `app.audit.audit_log()`:
- `auth.login`, `auth.login_failed`, `auth.register`
- `ticket.create`, `ticket.close`, `ticket.assign`, `ticket.update`, `ticket.delete`, `ticket.dedup`, `ticket.csv_export`
- `user.create`, `user.delete`
- `client.create`, `client.delete`
- `comment.create`, `comment.delete`
- `config.complete_setup`
- `service_account.create`, `service_account.delete`, `service_account.regenerate`

- `ticket.dedup` — auto-incremented when matching fingerprint found; also records each repetition timestamp in `Ticket.dedup_timestamps[]` JSON array
- When adding a new operation that modifies data, always call `audit_log()` after the change.

## Key Rules

1. Login by `name` (username), not email
2. `User.name` is unique — check for duplicates on create/update
3. Email uses `str` not `EmailStr` (flexible format)
4. Always import auth deps from `app.auth`, never from `app.routers.auth`
5. When adding new models, add them to `app/models/models.py`
6. When adding new routers, register them in `app/main.py` with prefix + tags
7. Keep inline Pydantic schemas in the router file (not in `schemas/`)
8. Always call `audit_log()` when modifying data (create, update, delete)
9. Test with `venv/bin/python test_e2e.py` or `venv/bin/python test_api.py` (use `sys.executable` in subprocess calls, not hardcoded `"python"`)
10. For FK cascade deletes, add `passive_deletes=True` to SQLAlchemy relationship on the parent side

## Database

- SQLite WAL mode + `PRAGMA foreign_keys=ON` set via `@event.listens_for(engine, "connect")`
- Foreign key cascade: `Comment.ondelete="CASCADE"` + `Ticket.comments` relationship has `passive_deletes=True`
- Always `rm -f peppermint.db` when schema changes (no migration system yet)

## Service Accounts / API Keys

- API Key format: `pep_<64_hex_chars>`, returned only on create/regenerate
- Key hash stored as PBKDF2, lookup by first 20 chars (`key_prefix`)
- Admin CRUD at `/api/v1/service-account` (POST/GET/DELETE + /{id}/regenerate)
- Frontend page at `/service-accounts` (admin only)
- API calls via API key are logged with `source="api"` in audit log

## Port

All servers and tests use **port 5003**.

## Environment Variables (`.env`)

```
SECRET_KEY=change-this-in-production
DATABASE_URL=sqlite:///./peppermint.db
```

## First-Time Setup Flow

1. No users exist → `first_time_setup = true` in Config
2. Register first user with `admin: true` → auto-allowed without auth
3. `POST /api/v1/config/complete-setup` (admin only) → sets `first_time_setup = false`
4. After that, all registrations require admin token

## Init Script

`venv/bin/python init.py` — menu-driven: option 1 rebuilds DB (deletes + recreates tables), option 2 registers admin (`admin` / `1qaz+2wsx`) + completes first-time setup.

## Seed Script

`venv/bin/python seed_tickets.py [count]` — generates random tickets via API. Auto-starts server + first-time setup if needed.

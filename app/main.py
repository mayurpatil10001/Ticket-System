"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import config
from app.core.exceptions import Forbidden, IllegalTransition, NotFound, ReasonRequired, ReopenWindowClosed
from app.db import SessionLocal, engine
from app.models import Base

logger = logging.getLogger(__name__)

# Create all tables (using create_all for speed — noted in README)
Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed the TicketCounter row if it doesn't exist
    from app.models.ticket_counter import TicketCounter

    with SessionLocal() as db:
        if not db.query(TicketCounter).filter(TicketCounter.id == 1).first():
            db.add(TicketCounter(id=1, last_number=0))
            db.commit()

    # Start escalation scheduler
    def _run_sweep():
        from app.services.escalation import auto_close_resolved, auto_resolve_awaiting, escalation_sweep

        with SessionLocal() as db:
            escalation_sweep(db)
            auto_resolve_awaiting(db)
            auto_close_resolved(db)

    scheduler.add_job(_run_sweep, "interval", seconds=60, id="escalation_sweep")
    scheduler.start()
    logger.info("Escalation scheduler started.")

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Concave Insights — Support Ticketing System",
    version="1.0.0",
    lifespan=lifespan,
)

# Session middleware (must come before routes)
app.add_middleware(
    SessionMiddleware,
    secret_key=config.secret_key,
    session_cookie="concave_session",
    max_age=86400 * 7,
    https_only=False,  # dev; set True in prod
    same_site="lax",
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---- Templates helper ----
from jinja2 import Environment, FileSystemLoader, select_autoescape

templates_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

IST = ZoneInfo("Asia/Kolkata")


def _ist_filter(dt):
    if dt is None:
        return "—"
    if hasattr(dt, "astimezone"):
        ist_dt = dt.astimezone(IST)
        day = str(ist_dt.day)          # no leading zero (cross-platform)
        hour = str(ist_dt.hour % 12 or 12)  # no leading zero
        minute = ist_dt.strftime("%M")
        ampm = "am" if ist_dt.hour < 12 else "pm"
        month = ist_dt.strftime("%b")
        year = ist_dt.strftime("%Y")
        return f"{day} {month} {year}, {hour}:{minute} {ampm} IST"
    return str(dt)


def _timesince_filter(dt):
    """Human-readable relative time, e.g. '12 min ago'."""
    if dt is None:
        return "—"
    from app.core.clock import clock
    from datetime import UTC

    now = clock.now()
    if not hasattr(dt, "tzinfo") or dt.tzinfo is None:
        from datetime import timezone
        dt = dt.replace(tzinfo=UTC)
    diff = now - dt
    s = int(diff.total_seconds())
    if s < 60:
        return "just now"
    elif s < 3600:
        return f"{s // 60} min ago"
    elif s < 86400:
        return f"{s // 3600}h ago"
    else:
        return f"{s // 86400}d ago"


templates_env.filters["ist"] = _ist_filter
templates_env.filters["timesince"] = _timesince_filter


def render(request: Request, template_name: str, context: dict) -> HTMLResponse:
    """Render a Jinja2 template with common context."""
    from app.core.csrf import get_csrf_token
    from app.db import SessionLocal
    from app.services.notification_service import unread_count

    ctx = {
        "request": request,
        "current_user": request.session.get("user_id"),
        "current_role": request.session.get("user_role"),
        "current_name": request.session.get("user_name"),
        **context,
    }
    # Inject unread notification count
    user_id = request.session.get("user_id")
    if user_id:
        with SessionLocal() as db:
            ctx["unread_count"] = unread_count(db, user_id)
    ctx["csrf_token"] = get_csrf_token(request)
    tmpl = templates_env.get_template(template_name)
    return HTMLResponse(tmpl.render(**ctx))


# ---- Register routes ----
from app.routes import auth, member_ui, agent_ui, head_ui
from app.routes import tickets_api, messages_api, actions_api
from app.routes import settings_api, dashboard_api, notifications_api
from app.routes import saved_replies_api, internal_api

app.include_router(auth.router)
app.include_router(member_ui.router)
app.include_router(agent_ui.router)
app.include_router(head_ui.router)
app.include_router(tickets_api.router, prefix="/api")
app.include_router(messages_api.router, prefix="/api")
app.include_router(actions_api.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(dashboard_api.router, prefix="/api")
app.include_router(notifications_api.router, prefix="/api")
app.include_router(saved_replies_api.router, prefix="/api")
app.include_router(internal_api.router, prefix="/api")


# ---- Health check ----
@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}


# ---- Global error handlers ----
from fastapi import status
from fastapi.responses import JSONResponse


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _is_api(request: Request) -> bool:
    return request.url.path.startswith("/api/")


@app.exception_handler(NotFound)
async def not_found_handler(request: Request, exc: NotFound):
    if _is_api(request) or _is_htmx(request):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": str(exc)}},
        )
    return render(request, "404.html", {"message": str(exc)})


@app.exception_handler(Forbidden)
async def forbidden_handler(request: Request, exc: Forbidden):
    if _is_api(request) or _is_htmx(request):
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "FORBIDDEN", "message": str(exc)}},
        )
    if not request.session.get("user_id"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)
    return render(request, "403.html", {"message": str(exc)})


@app.exception_handler(IllegalTransition)
async def illegal_transition_handler(request: Request, exc: IllegalTransition):
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "ILLEGAL_TRANSITION",
                "message": str(exc),
                "allowed": exc.allowed,
            }
        },
    )


@app.exception_handler(ReasonRequired)
async def reason_required_handler(request: Request, exc: ReasonRequired):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "REASON_REQUIRED",
                "message": str(exc),
                "field": exc.field,
            }
        },
    )


@app.exception_handler(ReopenWindowClosed)
async def reopen_window_handler(request: Request, exc: ReopenWindowClosed):
    return JSONResponse(
        status_code=409,
        content={"error": {"code": "REOPEN_WINDOW_CLOSED", "message": str(exc)}},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
    )


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    if _is_api(request):
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
        )
    return render(request, "500.html", {"message": "An unexpected error occurred."})

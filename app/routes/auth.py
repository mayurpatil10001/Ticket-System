"""Auth routes — login, logout, /api/me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, PasswordLoginRequest
from app.core.password import verify_password

router = APIRouter(tags=["auth"])


# ─────────────────────────────────────────────────────────────────────────────
# HTML login (password-based)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    from app.main import render

    if request.session.get("user_id"):
        role = request.session.get("user_role")
        return _redirect_for_role(role)

    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.role, User.name).all()
    return render(request, "login.html", {"users": users})


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, db: Session = Depends(get_db)):
    from app.main import render

    form = await request.form()
    email_raw = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))

    def fail(msg: str):
        users = db.query(User).filter(User.is_active.is_(True)).order_by(User.role, User.name).all()
        return render(request, "login.html", {"users": users, "error": msg, "prefill_email": email_raw})

    if not email_raw:
        return fail("Please enter your email address.")

    if not password:
        return fail("Password is required. Please enter your password to sign in.")

    user = db.query(User).filter(
        User.email == email_raw,
        User.is_active.is_(True),
    ).first()

    if not user:
        return fail("No account found with that email address.")

    if not user.password_hash:
        return fail("Account has no password set. Contact your admin.")

    if not verify_password(password, user.password_hash):
        return fail("Incorrect password. Please enter the correct password to continue.")

    request.session["user_id"] = user.id
    request.session["user_role"] = user.role
    request.session["user_name"] = user.name
    return _redirect_for_role(user.role)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/")
async def root(request: Request):
    role = request.session.get("user_role")
    if not role:
        return RedirectResponse(url="/login", status_code=302)
    return _redirect_for_role(role)


def _redirect_for_role(role: str | None) -> RedirectResponse:
    if role == "member":
        return RedirectResponse(url="/member/tickets", status_code=302)
    elif role == "agent":
        return RedirectResponse(url="/agent/queue", status_code=302)
    elif role == "head":
        return RedirectResponse(url="/head/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


# ─────────────────────────────────────────────────────────────────────────────
# JSON API (supports both test fixtures and password clients)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/auth/login")
async def api_login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = None
    if body.user_id is not None:
        user = db.get(User, body.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=404, detail="User not found.")
    elif body.email and body.password:
        user = db.query(User).filter(
            User.email == body.email.strip().lower(),
            User.is_active.is_(True),
        ).first()
        if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
    else:
        raise HTTPException(status_code=422, detail="Either user_id or (email and password) must be provided.")

    request.session["user_id"] = user.id
    request.session["user_role"] = user.role
    request.session["user_name"] = user.name
    return {"user_id": user.id, "role": user.role, "name": user.name}


@router.post("/api/auth/logout")
async def api_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/api/me")
async def api_me(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired.")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "upi_id": user.upi_id,
        "city": user.city,
        "dob": user.dob,
    }

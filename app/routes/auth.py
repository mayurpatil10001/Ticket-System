"""Auth routes — login, logout, /api/me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest

router = APIRouter(tags=["auth"])


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
    form = await request.form()
    user_id_raw = form.get("user_id", "")
    try:
        user_id = int(str(user_id_raw))
    except (ValueError, TypeError):
        users = db.query(User).filter(User.is_active.is_(True)).order_by(User.role, User.name).all()
        from app.main import render
        return render(request, "login.html", {"users": users, "error": "Invalid selection."})

    user = db.get(User, user_id)
    if not user or not user.is_active:
        from app.main import render
        users = db.query(User).filter(User.is_active.is_(True)).order_by(User.role, User.name).all()
        return render(request, "login.html", {"users": users, "error": "User not found."})

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


# --- JSON API ---
@router.post("/api/auth/login")
async def api_login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.get(User, body.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found.")
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

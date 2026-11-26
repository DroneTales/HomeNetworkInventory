# Home Network Inventory
# Login, logout, password change.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import time

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.constants import MIN_PASSWORD_LENGTH
from app.core.deps import get_current_user
from app.core.i18n import detect_language, translate
from app.core.security import hash_password, verify_password
from app.core.templating import render
from app.database import get_db
from app.models.user import User

router = APIRouter()

# Simple in-memory login rate limiter (single-process deployment).
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60
_login_attempts: dict[str, list[float]] = {}

def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"

def _is_login_limited(ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < LOGIN_WINDOW_SECONDS]
    _login_attempts[ip] = attempts
    return len(attempts) >= LOGIN_MAX_ATTEMPTS

def _record_login_failure(ip: str) -> None:
    _login_attempts.setdefault(ip, []).append(time.time())

def _reset_login_failures(ip: str) -> None:
    _login_attempts.pop(ip, None)

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is not None:
        return RedirectResponse("/", status_code=303)
    return render(request, "auth/login.html")

@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    lang = detect_language(request.headers.get("accept-language"))
    ip = _client_ip(request)

    if _is_login_limited(ip):
        return render(
            request,
            "auth/login.html",
            error=translate("auth.too_many_attempts", lang),
            username=username,
        )

    user = db.query(User).filter(User.username == username).first()

    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        _record_login_failure(ip)
        return render(
            request,
            "auth/login.html",
            error=translate("auth.invalid_credentials", lang),
            username=username,
        )

    _reset_login_failures(ip)
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

@router.get("/change-password", response_class=HTMLResponse)
def change_password_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    return render(
        request,
        "auth/change_password.html",
        user=user,
        must_change=user.must_change_password,
    )

@router.post("/change-password")
def change_password_submit(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    lang = user.language

    def render_error(msg_key: str, **fmt):
        message = translate(msg_key, lang)
        return render(
            request,
            "auth/change_password.html",
            user=user,
            must_change=user.must_change_password,
            error=message.format(**fmt) if fmt else message,
        )

    if not verify_password(old_password, user.password_hash):
        return render_error("auth.wrong_old_password")

    if new_password != confirm_password:
        return render_error("auth.passwords_mismatch")

    if len(new_password) < MIN_PASSWORD_LENGTH:
        return render_error("auth.password_too_short", n=MIN_PASSWORD_LENGTH)

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()

    return RedirectResponse("/", status_code=303)

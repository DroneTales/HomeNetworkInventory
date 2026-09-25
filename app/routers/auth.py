from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.i18n import detect_language, translate
from app.core.security import hash_password, verify_password
from app.core.templating import render
from app.database import get_db
from app.models.user import User

router = APIRouter()

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
    user = db.query(User).filter(User.username == username).first()

    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return render(
            request,
            "auth/login.html",
            error=translate(
                "auth.invalid_credentials",
                detect_language(request.headers.get("accept-language")),
            ),
            username=username,
        )

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

    def render_error(msg_key: str):
        return render(
            request,
            "auth/change_password.html",
            user=user,
            must_change=user.must_change_password,
            error=translate(msg_key, lang),
        )

    if not verify_password(old_password, user.password_hash):
        return render_error("auth.wrong_old_password")

    if new_password != confirm_password:
        return render_error("auth.passwords_mismatch")

    if len(new_password) < 1:
        return render_error("auth.passwords_mismatch")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()

    return RedirectResponse("/", status_code=303)

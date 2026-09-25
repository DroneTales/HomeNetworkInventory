from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.crud import user as crud_user
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("", response_class=HTMLResponse)
def view_profile(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    warning = request.session.pop("warning", None)
    return render(request, "profile/view.html", user=user, warning=warning)

@router.post("/preferences")
async def update_preferences(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    form = await request.form()
    language = (form.get("language") or "en").strip().lower()
    theme = (form.get("theme") or "auto").strip().lower()

    try:
        crud_user.update_preferences(
            db,
            user_id=user.id,
            language=language,
            theme=theme,
        )
        db.commit()
    except ValidationError as e:
        db.rollback()
        return render(
            request,
            "profile/view.html",
            user=user,
            error=e.message,
        )

    request.session["warning"] = "Preferences saved."
    return RedirectResponse("/profile", status_code=303)

@router.post("/change-password")
async def change_password(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    form = await request.form()
    old_password = (form.get("old_password") or "").strip()
    new_password = (form.get("new_password") or "").strip()
    confirm_password = (form.get("confirm_password") or "").strip()

    from app.core.i18n import translate

    def render_error(msg_key: str):
        return render(
            request,
            "profile/view.html",
            user=user,
            error=translate(msg_key, user.language),
        )

    if new_password != confirm_password:
        return render_error("auth.passwords_mismatch")

    if len(new_password) < 1:
        return render_error("auth.passwords_mismatch")

    try:
        crud_user.change_own_password(
            db,
            user_id=user.id,
            old_password=old_password,
            new_password=new_password,
        )
        db.commit()
    except ValidationError:
        db.rollback()
        return render_error("auth.wrong_old_password")

    warning = None
    if len(new_password) < 5:
        warning = "Password changed. Warning: it is shorter than 5 characters."

    request.session["warning"] = warning or "Password changed."
    return RedirectResponse("/profile", status_code=303)

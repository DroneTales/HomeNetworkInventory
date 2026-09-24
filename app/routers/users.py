from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.crud import site as crud_site
from app.crud import user as crud_user
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


# ---------- Список пользователей ----------

@router.get("")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    users = crud_user.list_all(db)
    warning = request.session.pop("warning", None)
    return render(
        request,
        "users/list.html",
        user=user,
        users=users,
        warning=warning,
    )


# ---------- Создание ----------

@router.get("/new", response_class=HTMLResponse)
def new_user_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    return render(
        request,
        "users/form.html",
        user=user,
        form_action="/users/new",
        is_edit=False,
        form_data={},
        target_user=None,
        all_sites=[],
        assigned_sites=[],
    )


@router.post("/new")
async def new_user_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    form = await request.form()
    data = _collect_form(form)

    try:
        created_user = crud_user.create(
            db,
            username=data["username"],
            password=data["password"],
            role=data["role"],
            can_edit=data["can_edit"],
            can_view_passwords=data["can_view_passwords"],
            can_change_passwords=data["can_change_passwords"],
            must_change_password=data["must_change_password"],
            is_active=data["is_active"],
            language=data["language"],
            theme=data["theme"],
        )
        db.commit()
    except ValidationError as e:
        db.rollback()
        return render(
            request,
            "users/form.html",
            user=user,
            form_action="/users/new",
            is_edit=False,
            error=e.message,
            form_data=data,
            target_user=None,
            all_sites=[],
            assigned_sites=[],
        )

    if len(data["password"]) < 5:
        request.session["warning"] = (
            f"Saved. Password for user '{created_user.username}' is shorter than 5 characters."
        )

    return RedirectResponse("/users", status_code=303)


# ---------- Редактирование ----------

@router.get("/{user_id}/edit", response_class=HTMLResponse)
def edit_user_form(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = crud_user.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    form_data = {
        "username": target.username,
        "role": target.role,
        "can_edit": target.can_edit,
        "can_view_passwords": target.can_view_passwords,
        "can_change_passwords": target.can_change_passwords,
        "is_active": target.is_active,
        "language": target.language,
        "theme": target.theme,
    }

    all_sites = crud_site.list_all(db, include_inactive=False)
    assigned_site_ids = {us.site_id for us in target.user_sites}
    assigned_sites = [s for s in all_sites if s.id in assigned_site_ids]

    return render(
        request,
        "users/form.html",
        user=user,
        form_action=f"/users/{user_id}/edit",
        is_edit=True,
        target_user=target,
        form_data=form_data,
        all_sites=all_sites,
        assigned_sites=assigned_sites,
    )


@router.post("/{user_id}/edit")
async def edit_user_submit(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = crud_user.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    form = await request.form()
    data = _collect_form(form)

    try:
        crud_user.update(
            db,
            user_id=user_id,
            username=data["username"],
            role=data["role"],
            can_edit=data["can_edit"],
            can_view_passwords=data["can_view_passwords"],
            can_change_passwords=data["can_change_passwords"],
            is_active=data["is_active"],
            language=data["language"],
            theme=data["theme"],
        )
        db.commit()
    except ValidationError as e:
        db.rollback()
        all_sites = crud_site.list_all(db, include_inactive=False)
        assigned_site_ids = {us.site_id for us in target.user_sites}
        assigned_sites = [s for s in all_sites if s.id in assigned_site_ids]
        return render(
            request,
            "users/form.html",
            user=user,
            form_action=f"/users/{user_id}/edit",
            is_edit=True,
            target_user=target,
            error=e.message,
            form_data=data,
            all_sites=all_sites,
            assigned_sites=assigned_sites,
        )

    return RedirectResponse("/users", status_code=303)


# ---------- Назначение домов ----------

@router.post("/{user_id}/sites/add")
async def add_site_to_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = crud_user.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    form = await request.form()
    site_id_raw = (form.get("site_id") or "").strip()
    try:
        site_id = int(site_id_raw)
    except (TypeError, ValueError):
        return RedirectResponse(f"/users/{user_id}/edit", status_code=303)

    try:
        crud_site.assign_user(db, user_id=user_id, site_id=site_id)
        db.commit()
    except ValidationError:
        db.rollback()

    return RedirectResponse(f"/users/{user_id}/edit", status_code=303)


@router.post("/{user_id}/sites/{site_id}/remove")
def remove_site_from_user(
    user_id: int,
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = crud_user.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    crud_site.unassign_user(db, user_id=user_id, site_id=site_id)
    db.commit()
    return RedirectResponse(f"/users/{user_id}/edit", status_code=303)


# ---------- Сброс пароля ----------

@router.get("/{user_id}/reset-password", response_class=HTMLResponse)
def reset_password_form(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = crud_user.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    return render(
        request,
        "users/reset_password.html",
        user=user,
        target_user=target,
        form_action=f"/users/{user_id}/reset-password",
        form_data={},
    )


@router.post("/{user_id}/reset-password")
async def reset_password_submit(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = crud_user.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    form = await request.form()
    new_password = (form.get("new_password") or "").strip()
    must_change = form.get("must_change_password") == "on"

    try:
        crud_user.reset_password(
            db,
            user_id=user_id,
            new_password=new_password,
            must_change_password=must_change,
        )
        db.commit()
    except ValidationError as e:
        db.rollback()
        return render(
            request,
            "users/reset_password.html",
            user=user,
            target_user=target,
            form_action=f"/users/{user_id}/reset-password",
            error=e.message,
            form_data={"new_password": new_password, "must_change_password": must_change},
        )

    if len(new_password) < 5:
        request.session["warning"] = (
            f"Password for '{target.username}' reset. "
            f"Warning: it is shorter than 5 characters."
        )

    return RedirectResponse("/users", status_code=303)


# ---------- Удаление ----------

@router.post("/{user_id}/delete")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = crud_user.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        crud_user.delete(db, user_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        from urllib.parse import quote
        return RedirectResponse(
            f"/users?error={quote(e.message)}",
            status_code=303,
        )

    return RedirectResponse("/users", status_code=303)


# ---------- Вспомогательное ----------

def _collect_form(form) -> dict:
    return {
        "username": (form.get("username") or "").strip(),
        "password": (form.get("password") or "").strip(),
        "role": (form.get("role") or "user").strip().lower(),
        "can_edit": form.get("can_edit") == "on",
        "can_view_passwords": form.get("can_view_passwords") == "on",
        "can_change_passwords": form.get("can_change_passwords") == "on",
        "must_change_password": form.get("must_change_password") == "on",
        "is_active": form.get("is_active") == "on",
        "language": (form.get("language") or "en").strip().lower(),
        "theme": (form.get("theme") or "auto").strip().lower(),
    }


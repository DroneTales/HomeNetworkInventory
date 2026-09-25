from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.deps import (
    clear_current_site_cookie,
    get_accessible_sites,
    require_admin,
    require_user,
    set_current_site_cookie,
    user_can_access_site,
)
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.crud import site as crud_site
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/sites", tags=["sites"])

MAX_PHOTO_BYTES = 2 * 1024 * 1024
ALLOWED_PHOTO_MIME = {"image/jpeg", "image/png"}

@router.get("")
def list_sites(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    sites = get_accessible_sites(db, user)

    if len(sites) == 1 and user.role != "admin":
        response = RedirectResponse("/devices", status_code=303)
        set_current_site_cookie(response, sites[0].id)
        return response

    error = request.query_params.get("error")
    return render(
        request,
        "sites/list.html",
        user=user,
        sites=sites,
        error=error,
    )

@router.get("/switch")
@router.post("/switch")
def switch_site(user: User = Depends(require_user)):
    response = RedirectResponse("/sites", status_code=303)
    clear_current_site_cookie(response)
    return response

@router.get("/{site_id}/select")
@router.post("/{site_id}/select")
def select_site(
    site_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    site = crud_site.get_by_id(db, site_id)
    if site is None or not site.is_active:
        raise HTTPException(status_code=404, detail="Home not found")
    if not user_can_access_site(db, user, site_id):
        raise HTTPException(status_code=404, detail="Home not found")

    response = RedirectResponse("/devices", status_code=303)
    set_current_site_cookie(response, site_id)
    return response

@router.get("/new", response_class=HTMLResponse)
def new_site_form(
    request: Request,
    user: User = Depends(require_admin),
):
    return render(
        request,
        "sites/form.html",
        user=user,
        form_action="/sites/new",
        is_edit=False,
        form_data={},
        site=None,
    )

@router.post("/new")
async def new_site_submit(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    form = await request.form()
    name = (form.get("name") or "").strip()
    address = (form.get("address") or "").strip() or None
    is_active = form.get("is_active") == "on"

    try:
        photo_bytes, photo_mime = await _extract_photo(form)
        crud_site.create(
            db,
            name=name,
            address=address,
            photo=photo_bytes,
            photo_mime=photo_mime,
            is_active=is_active,
        )
        db.commit()
    except ValidationError as e:
        db.rollback()
        return render(
            request,
            "sites/form.html",
            user=user,
            form_action="/sites/new",
            is_edit=False,
            site=None,
            error=e.message,
            form_data={"name": name, "address": address or "", "is_active": is_active},
        )

    return RedirectResponse("/sites", status_code=303)

@router.get("/{site_id}/edit", response_class=HTMLResponse)
def edit_site_form(
    site_id: int,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    site = crud_site.get_by_id(db, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Home not found")

    return render(
        request,
        "sites/form.html",
        user=user,
        form_action=f"/sites/{site_id}/edit",
        is_edit=True,
        site=site,
        form_data={
            "name": site.name,
            "address": site.address or "",
            "is_active": site.is_active,
        },
    )

@router.post("/{site_id}/edit")
async def edit_site_submit(
    site_id: int,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    site = crud_site.get_by_id(db, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Home not found")

    form = await request.form()
    name = (form.get("name") or "").strip()
    address = (form.get("address") or "").strip() or None
    is_active = form.get("is_active") == "on"
    remove_photo = form.get("remove_photo") == "on"

    try:
        photo_bytes, photo_mime = await _extract_photo(form)
        crud_site.update(
            db,
            site_id=site_id,
            name=name,
            address=address,
            photo=photo_bytes,
            photo_mime=photo_mime,
            is_active=is_active,
        )
        if remove_photo and photo_bytes is None:
            crud_site.clear_photo(db, site_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return render(
            request,
            "sites/form.html",
            user=user,
            form_action=f"/sites/{site_id}/edit",
            is_edit=True,
            site=site,
            error=e.message,
            form_data={"name": name, "address": address or "", "is_active": is_active},
        )

    return RedirectResponse("/sites", status_code=303)

@router.post("/{site_id}/delete")
def delete_site(
    site_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    site = crud_site.get_by_id(db, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Home not found")

    try:
        crud_site.delete(db, site_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return RedirectResponse(
            f"/sites?error={quote(e.message)}",
            status_code=303,
        )

    return RedirectResponse("/sites", status_code=303)

@router.get("/{site_id}/photo")
def site_photo(
    site_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not user_can_access_site(db, user, site_id):
        raise HTTPException(status_code=404, detail="Photo not found")

    site = crud_site.get_by_id(db, site_id)
    if site is None or not site.photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return Response(
        content=site.photo,
        media_type=site.photo_mime or "image/jpeg",
    )

async def _extract_photo(form) -> tuple[bytes | None, str | None]:
    file = form.get("photo")
    if file is None or not hasattr(file, "read"):
        return None, None

    content = await file.read()
    if not content:
        return None, None

    if len(content) > MAX_PHOTO_BYTES:
        raise ValidationError(
            f"Photo is too large. Maximum is {MAX_PHOTO_BYTES // (1024 * 1024)} MB.",
            field="photo",
        )

    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_PHOTO_MIME:
        raise ValidationError(
            "Photo must be JPEG or PNG.",
            field="photo",
        )

    return content, mime

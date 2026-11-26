# Home Network Inventory
# Reference CRUD UI: locations.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.deps import require_edit, require_site
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.core.utils import redirect_with_error
from app.crud import location as crud_location
from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.routers.reference_ui.base import router, _ref_form

@router.get("/locations", response_class=HTMLResponse)
def locations_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    items = crud_location.list_all(db, site.id)
    rows = [{"id": x.id, "cells": [x.name, x.description or "—"]} for x in items]
    return render(
        request,
        "reference/list.html",
        user=user,
        current_site=site,
        title_key="reference.title.locations",
        add_url="/reference/locations/new",
        edit_url_prefix="/reference/locations/",
        delete_url_prefix="/reference/locations/",
        column_keys=["devices.list.name", "devices.form.field.description"],
        rows=rows,
    )

@router.get("/locations/new", response_class=HTMLResponse)
def locations_new_form(
    request: Request,
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    return _ref_form(
            request,
            user,
            site,
            "reference/location_form.html",
            "/reference/locations/new",
            False,
            {},
    )

@router.post("/locations/new")
async def locations_new_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()
    description = (form.get("description") or "").strip() or None

    try:
        crud_location.create(db, site_id=site.id, name=name, description=description)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/location_form.html",
            "/reference/locations/new",
            False,
            {"name": name, "description": description or ""},
            error=e.message,
        )
    return RedirectResponse("/reference/locations", status_code=303)

@router.get("/locations/{item_id}/edit", response_class=HTMLResponse)
def locations_edit_form(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    item = crud_location.get_by_id(db, item_id, site_id=site.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _ref_form(
            request,
            user,
            site,
            "reference/location_form.html",
            f"/reference/locations/{item_id}/edit",
            True,
            {"name": item.name, "description": item.description or ""},
        )

@router.post("/locations/{item_id}/edit")
async def locations_edit_submit(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    item = crud_location.get_by_id(db, item_id, site_id=site.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")

    form = await request.form()
    name = (form.get("name") or "").strip()
    description = (form.get("description") or "").strip() or None

    try:
        crud_location.update(db, location_id=item_id, name=name, description=description)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/location_form.html",
            f"/reference/locations/{item_id}/edit",
            True,
            {"name": name, "description": description or ""},
            error=e.message,
        )
    return RedirectResponse("/reference/locations", status_code=303)

@router.post("/locations/{item_id}/delete")
def locations_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    item = crud_location.get_by_id(db, item_id, site_id=site.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        crud_location.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return redirect_with_error("/reference/locations", e.message)
    return RedirectResponse("/reference/locations", status_code=303)

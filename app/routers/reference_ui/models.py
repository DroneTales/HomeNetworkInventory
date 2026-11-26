# Home Network Inventory
# Reference CRUD UI: models.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.deps import require_admin, require_site
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.core.utils import redirect_with_error, to_int
from app.crud import model as crud_model, vendor as crud_vendor
from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.routers.reference_ui.base import router, _ref_form

@router.get("/models", response_class=HTMLResponse)
def models_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    items = crud_model.list_all(db)
    rows = [
        {"id": x.id, "cells": [x.vendor.name if x.vendor else "—", x.name]}
        for x in items
    ]
    return render(
        request,
        "reference/list.html",
        user=user,
        current_site=site,
        title_key="reference.title.models",
        add_url="/reference/models/new",
        edit_url_prefix="/reference/models/",
        delete_url_prefix="/reference/models/",
        column_keys=["devices.list.vendor", "devices.list.name"],
        rows=rows,
    )

@router.get("/models/new", response_class=HTMLResponse)
def models_new_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    vendors = crud_vendor.list_all(db)
    return _ref_form(
            request,
            user,
            site,
            "reference/model_form.html",
            "/reference/models/new",
            False,
            {},
        vendors=vendors,
    )

@router.post("/models/new")
async def models_new_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()
    vendor_id = to_int(form.get("vendor_id"))

    try:
        crud_model.create(db, vendor_id=vendor_id, name=name)
        db.commit()
    except ValidationError as e:
        db.rollback()
        vendors = crud_vendor.list_all(db)
        return _ref_form(
            request,
            user,
            site,
            "reference/model_form.html",
            "/reference/models/new",
            False,
            {"name": name, "vendor_id": vendor_id or ""},
            error=e.message,
            vendors=vendors,
        )
    return RedirectResponse("/reference/models", status_code=303)

@router.get("/models/{item_id}/edit", response_class=HTMLResponse)
def models_edit_form(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    item = crud_model.get_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    vendors = crud_vendor.list_all(db)
    return _ref_form(
            request,
            user,
            site,
            "reference/model_form.html",
            f"/reference/models/{item_id}/edit",
            True,
            {"name": item.name, "vendor_id": item.vendor_id},
            vendors=vendors,
        )

@router.post("/models/{item_id}/edit")
async def models_edit_submit(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()
    vendor_id = to_int(form.get("vendor_id"))

    try:
        crud_model.update(db, model_id=item_id, vendor_id=vendor_id, name=name)
        db.commit()
    except ValidationError as e:
        db.rollback()
        vendors = crud_vendor.list_all(db)
        return _ref_form(
            request,
            user,
            site,
            "reference/model_form.html",
            f"/reference/models/{item_id}/edit",
            True,
            {"name": name, "vendor_id": vendor_id or ""},
            error=e.message,
            vendors=vendors,
        )
    return RedirectResponse("/reference/models", status_code=303)

@router.post("/models/{item_id}/delete")
def models_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    try:
        crud_model.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return redirect_with_error("/reference/models", e.message)
    return RedirectResponse("/reference/models", status_code=303)

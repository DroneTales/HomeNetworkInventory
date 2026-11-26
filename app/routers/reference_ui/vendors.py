# Home Network Inventory
# Reference CRUD UI: vendors.
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
from app.core.utils import redirect_with_error
from app.crud import vendor as crud_vendor
from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.routers.reference_ui.base import router, _ref_form

@router.get("/vendors", response_class=HTMLResponse)
def vendors_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    items = crud_vendor.list_all(db)
    rows = [{"id": x.id, "cells": [x.name]} for x in items]
    return render(
        request,
        "reference/list.html",
        user=user,
        current_site=site,
        title_key="reference.title.vendors",
        add_url="/reference/vendors/new",
        edit_url_prefix="/reference/vendors/",
        delete_url_prefix="/reference/vendors/",
        column_keys=["devices.list.name"],
        rows=rows,
    )

@router.get("/vendors/new", response_class=HTMLResponse)
def vendors_new_form(
    request: Request,
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    return _ref_form(
            request,
            user,
            site,
            "reference/vendor_form.html",
            "/reference/vendors/new",
            False,
            {},
    )

@router.post("/vendors/new")
async def vendors_new_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()

    try:
        crud_vendor.create(db, name=name)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/vendor_form.html",
            "/reference/vendors/new",
            False,
            {"name": name},
            error=e.message,
        )
    return RedirectResponse("/reference/vendors", status_code=303)

@router.get("/vendors/{item_id}/edit", response_class=HTMLResponse)
def vendors_edit_form(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    item = crud_vendor.get_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _ref_form(
            request,
            user,
            site,
            "reference/vendor_form.html",
            f"/reference/vendors/{item_id}/edit",
            True,
            {"name": item.name},
        )

@router.post("/vendors/{item_id}/edit")
async def vendors_edit_submit(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()

    try:
        crud_vendor.update(db, vendor_id=item_id, name=name)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/vendor_form.html",
            f"/reference/vendors/{item_id}/edit",
            True,
            {"name": name},
            error=e.message,
        )
    return RedirectResponse("/reference/vendors", status_code=303)

@router.post("/vendors/{item_id}/delete")
def vendors_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    try:
        crud_vendor.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return redirect_with_error("/reference/vendors", e.message)
    return RedirectResponse("/reference/vendors", status_code=303)

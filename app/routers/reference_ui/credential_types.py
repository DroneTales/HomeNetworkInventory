# Home Network Inventory
# Reference CRUD UI: credential types.
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
from app.crud import credential_type as crud_cred_type
from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.routers.reference_ui.base import router, _ref_form

@router.get("/credential-types", response_class=HTMLResponse)
def credential_types_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    items = crud_cred_type.list_all(db)
    rows = [{"id": x.id, "cells": [x.name, x.description or "—"]} for x in items]
    return render(
        request,
        "reference/list.html",
        user=user,
        current_site=site,
        title_key="reference.title.credential_types",
        add_url="/reference/credential-types/new",
        edit_url_prefix="/reference/credential-types/",
        delete_url_prefix="/reference/credential-types/",
        column_keys=["devices.list.name", "devices.form.field.description"],
        rows=rows,
    )

@router.get("/credential-types/new", response_class=HTMLResponse)
def credential_types_new_form(
    request: Request,
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    return _ref_form(
            request,
            user,
            site,
            "reference/credential_type_form.html",
            "/reference/credential-types/new",
            False,
            {},
    )

@router.post("/credential-types/new")
async def credential_types_new_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()
    description = (form.get("description") or "").strip() or None

    try:
        crud_cred_type.create(db, name=name, description=description)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            site,
            "reference/credential_type_form.html",
            "/reference/credential-types/new",
            False,
            {"name": name, "description": description or ""},
            error=e.message,
        )
    return RedirectResponse("/reference/credential-types", status_code=303)

@router.get("/credential-types/{item_id}/edit", response_class=HTMLResponse)
def credential_types_edit_form(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    item = crud_cred_type.get_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _ref_form(
            request,
            user,
            site,
            "reference/credential_type_form.html",
            f"/reference/credential-types/{item_id}/edit",
            True,
            {"name": item.name, "description": item.description or ""},
        )

@router.post("/credential-types/{item_id}/edit")
async def credential_types_edit_submit(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()
    description = (form.get("description") or "").strip() or None

    try:
        crud_cred_type.update(db, type_id=item_id, name=name, description=description)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/credential_type_form.html",
            f"/reference/credential-types/{item_id}/edit",
            True,
            {"name": name, "description": description or ""},
            error=e.message,
        )
    return RedirectResponse("/reference/credential-types", status_code=303)

@router.post("/credential-types/{item_id}/delete")
def credential_types_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    try:
        crud_cred_type.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return redirect_with_error("/reference/credential-types", e.message)
    return RedirectResponse("/reference/credential-types", status_code=303)

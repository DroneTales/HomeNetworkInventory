# Home Network Inventory
# Reference CRUD UI: networks.
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
from app.core.utils import redirect_with_error, to_int
from app.crud import network as crud_network
from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.routers.reference_ui.base import router, _ref_form

@router.get("/networks", response_class=HTMLResponse)
def networks_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    items = crud_network.list_all(db, site.id)
    rows = [
        {
            "id": x.id,
            "cells": [
                x.name,
                f"{x.network_address}/{x.mask}",
                x.vlan if x.vlan is not None else "—",
            ],
        }
        for x in items
    ]
    return render(
        request,
        "reference/list.html",
        user=user,
        current_site=site,
        title_key="reference.title.networks",
        add_url="/reference/networks/new",
        edit_url_prefix="/reference/networks/",
        delete_url_prefix="/reference/networks/",
        column_keys=["devices.list.name", "reference.col.address", "reference.field.vlan"],
        rows=rows,
    )

@router.get("/networks/new", response_class=HTMLResponse)
def networks_new_form(
    request: Request,
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    return _ref_form(
            request,
            user,
            site,
            "reference/network_form.html",
            "/reference/networks/new",
            False,
            {},
    )

@router.post("/networks/new")
async def networks_new_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    form = await request.form()
    data = _network_form_data(form)

    try:
        crud_network.create(db, site_id=site.id, **data)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/network_form.html",
            "/reference/networks/new",
            is_edit=False,
            error=e.message,
            form_data=data,
        )
    return RedirectResponse("/reference/networks", status_code=303)

@router.get("/networks/{item_id}/edit", response_class=HTMLResponse)
def networks_edit_form(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    item = crud_network.get_by_id(db, item_id, site_id=site.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _ref_form(
        request,
        user,
        site,
        "reference/network_form.html",
        f"/reference/networks/{item_id}/edit",
        True,
        {
            "name": item.name,
            "network_address": item.network_address,
            "mask": item.mask,
            "vlan": item.vlan if item.vlan is not None else "",
            "description": item.description or "",
        },
    )

@router.post("/networks/{item_id}/edit")
async def networks_edit_submit(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    item = crud_network.get_by_id(db, item_id, site_id=site.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")

    form = await request.form()
    data = _network_form_data(form)

    try:
        crud_network.update(db, network_id=item_id, **data)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/network_form.html",
            f"/reference/networks/{item_id}/edit",
            is_edit=True,
            error=e.message,
            form_data=data,
        )
    return RedirectResponse("/reference/networks", status_code=303)

@router.post("/networks/{item_id}/delete")
def networks_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    item = crud_network.get_by_id(db, item_id, site_id=site.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        crud_network.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return redirect_with_error("/reference/networks", e.message)
    return RedirectResponse("/reference/networks", status_code=303)

def _network_form_data(form) -> dict:
    return {
        "name": (form.get("name") or "").strip(),
        "network_address": (form.get("network_address") or "").strip(),
        "mask": (form.get("mask") or "").strip(),
        "vlan": to_int(form.get("vlan")),
        "description": (form.get("description") or "").strip() or None,
    }

# Home Network Inventory
# Reference CRUD UI: device types.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Depends, HTTPException, Request
from markupsafe import Markup
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.deps import require_admin, require_site
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.core.utils import redirect_with_error
from app.crud import device_type as crud_device_type
from app.core.icons import AVAILABLE_ICONS
from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.routers.reference_ui.base import router, _ref_form

@router.get("/device-types", response_class=HTMLResponse)
def device_types_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    items = crud_device_type.list_all(db)
    rows = []
    for x in items:
        # Build icon HTML
        if x.icon:
            icon_html = f'<i class="icon icon-{x.icon} text-primary" style="font-size: 1.75rem;"></i>'
        else:
            icon_html = '<i class="icon icon-other text-muted" style="font-size: 1.75rem;"></i>'
        
        rows.append({
            "id": x.id,
            "cells": [
                Markup(icon_html),
                x.name,
                "✓" if x.is_active else "—",
                "✓" if x.supports_port_forwarding else "—",
                x.description or "—"
            ],
        })
    return render(
        request,
        "reference/list.html",
        user=user,
        current_site=site,
        title_key="reference.title.device_types",
        add_url="/reference/device-types/new",
        edit_url_prefix="/reference/device-types/",
        delete_url_prefix="/reference/device-types/",
        column_keys=["reference.col.icon", "devices.list.name", "devices.form.field.active", "reference.col.pf", "devices.form.field.description"],
        rows=rows,
    )

@router.get("/device-types/new", response_class=HTMLResponse)
def device_types_new_form(
    request: Request,
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    return _ref_form(
            request,
            user,
            site,
            "reference/device_type_form.html",
            "/reference/device-types/new",
            False,
            {"is_active": True, "supports_port_forwarding": False},
            available_icons=AVAILABLE_ICONS,
        )

@router.post("/device-types/new")
async def device_types_new_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()
    is_active = form.get("is_active") == "on"
    supports_pf = form.get("supports_port_forwarding") == "on"
    description = (form.get("description") or "").strip() or None
    icon = (form.get("icon") or "").strip() or None

    try:
        crud_device_type.create(db, name=name, is_active=is_active, supports_port_forwarding=supports_pf, description=description, icon=icon)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/device_type_form.html",
            "/reference/device-types/new",
            False,
            {"name": name, "is_active": is_active, "supports_port_forwarding": supports_pf, "description": description or ""},
            error=e.message,
        )
    return RedirectResponse("/reference/device-types", status_code=303)

@router.get("/device-types/{item_id}/edit", response_class=HTMLResponse)
def device_types_edit_form(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    item = crud_device_type.get_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _ref_form(
            request,
            user,
            site,
            "reference/device_type_form.html",
            f"/reference/device-types/{item_id}/edit",
            True,
            {
            "name": item.name,
            "is_active": item.is_active,
            "supports_port_forwarding": item.supports_port_forwarding,
            "description": item.description or "",
            "icon": item.icon or "",
        },
            available_icons=AVAILABLE_ICONS,
        )

@router.post("/device-types/{item_id}/edit")
async def device_types_edit_submit(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    form = await request.form()
    name = (form.get("name") or "").strip()
    is_active = form.get("is_active") == "on"
    supports_pf = form.get("supports_port_forwarding") == "on"
    description = (form.get("description") or "").strip() or None
    icon = (form.get("icon") or "").strip() or None

    try:
        crud_device_type.update(
            db, type_id=item_id, name=name, is_active=is_active, supports_port_forwarding=supports_pf, description=description, icon=icon
        )
        db.commit()
    except ValidationError as e:
        db.rollback()
        return _ref_form(
            request,
            user,
            site,
            "reference/device_type_form.html",
            f"/reference/device-types/{item_id}/edit",
            True,
            {"name": name, "is_active": is_active, "supports_port_forwarding": supports_pf, "description": description or ""},
            error=e.message,
        )
    return RedirectResponse("/reference/device-types", status_code=303)

@router.post("/device-types/{item_id}/delete")
def device_types_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    try:
        crud_device_type.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return redirect_with_error("/reference/device-types", e.message)
    return RedirectResponse("/reference/device-types", status_code=303)

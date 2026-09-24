from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_admin, require_edit, require_site
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.crud import credential_type as crud_cred_type
from app.crud import device_type as crud_device_type
from app.crud import location as crud_location
from app.crud import model as crud_model
from app.crud import network as crud_network
from app.crud import vendor as crud_vendor
from app.database import get_db
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/reference", tags=["reference-ui"])


# ---------- Индекс ----------

@router.get("", response_class=HTMLResponse)
def reference_index(
    request: Request,
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    return render(
        request,
        "reference/index.html",
        user=user,
        current_site=site,
    )


# ============================================================
# Locations (привязаны к дому, доступны с правом Can edit)
# ============================================================

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
        title="Locations",
        add_url="/reference/locations/new",
        edit_url_prefix="/reference/locations/",
        delete_url_prefix="/reference/locations/",
        columns=["Name", "Description"],
        rows=rows,
    )


@router.get("/locations/new", response_class=HTMLResponse)
def locations_new_form(
    request: Request,
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    return render(
        request,
        "reference/location_form.html",
        user=user,
        current_site=site,
        form_action="/reference/locations/new",
        is_edit=False,
        form_data={},
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
        return render(
            request,
            "reference/location_form.html",
            user=user,
            current_site=site,
            form_action="/reference/locations/new",
            is_edit=False,
            error=e.message,
            form_data={"name": name, "description": description or ""},
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
    return render(
        request,
        "reference/location_form.html",
        user=user,
        current_site=site,
        form_action=f"/reference/locations/{item_id}/edit",
        is_edit=True,
        form_data={"name": item.name, "description": item.description or ""},
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
        return render(
            request,
            "reference/location_form.html",
            user=user,
            current_site=site,
            form_action=f"/reference/locations/{item_id}/edit",
            is_edit=True,
            error=e.message,
            form_data={"name": name, "description": description or ""},
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

    from urllib.parse import quote
    try:
        crud_location.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return RedirectResponse(
            f"/reference/locations?error={quote(e.message)}",
            status_code=303,
        )
    return RedirectResponse("/reference/locations", status_code=303)


# ============================================================
# Device Types (глобальные, только admin)
# ============================================================

@router.get("/device-types", response_class=HTMLResponse)
def device_types_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    items = crud_device_type.list_all(db)
    rows = [
        {
            "id": x.id,
            "cells": [x.name, "yes" if x.is_active else "no", x.description or "—"],
        }
        for x in items
    ]
    return render(
        request,
        "reference/list.html",
        user=user,
        current_site=site,
        title="Device Types",
        add_url="/reference/device-types/new",
        edit_url_prefix="/reference/device-types/",
        delete_url_prefix="/reference/device-types/",
        columns=["Name", "Active", "Description"],
        rows=rows,
    )


@router.get("/device-types/new", response_class=HTMLResponse)
def device_types_new_form(
    request: Request,
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    return render(
        request,
        "reference/device_type_form.html",
        user=user,
        current_site=site,
        form_action="/reference/device-types/new",
        is_edit=False,
        form_data={"is_active": True},
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
    description = (form.get("description") or "").strip() or None

    try:
        crud_device_type.create(db, name=name, is_active=is_active, description=description)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return render(
            request,
            "reference/device_type_form.html",
            user=user,
            current_site=site,
            form_action="/reference/device-types/new",
            is_edit=False,
            error=e.message,
            form_data={"name": name, "is_active": is_active, "description": description or ""},
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
    return render(
        request,
        "reference/device_type_form.html",
        user=user,
        current_site=site,
        form_action=f"/reference/device-types/{item_id}/edit",
        is_edit=True,
        form_data={
            "name": item.name,
            "is_active": item.is_active,
            "description": item.description or "",
        },
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
    description = (form.get("description") or "").strip() or None

    try:
        crud_device_type.update(
            db, type_id=item_id, name=name, is_active=is_active, description=description
        )
        db.commit()
    except ValidationError as e:
        db.rollback()
        return render(
            request,
            "reference/device_type_form.html",
            user=user,
            current_site=site,
            form_action=f"/reference/device-types/{item_id}/edit",
            is_edit=True,
            error=e.message,
            form_data={"name": name, "is_active": is_active, "description": description or ""},
        )
    return RedirectResponse("/reference/device-types", status_code=303)


@router.post("/device-types/{item_id}/delete")
def device_types_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    from urllib.parse import quote
    try:
        crud_device_type.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return RedirectResponse(
            f"/reference/device-types?error={quote(e.message)}",
            status_code=303,
        )
    return RedirectResponse("/reference/device-types", status_code=303)


# ============================================================
# Vendors (глобальные, только admin)
# ============================================================

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
        title="Vendors",
        add_url="/reference/vendors/new",
        edit_url_prefix="/reference/vendors/",
        delete_url_prefix="/reference/vendors/",
        columns=["Name"],
        rows=rows,
    )


@router.get("/vendors/new", response_class=HTMLResponse)
def vendors_new_form(
    request: Request,
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    return render(
        request,
        "reference/vendor_form.html",
        user=user,
        current_site=site,
        form_action="/reference/vendors/new",
        is_edit=False,
        form_data={},
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
        return render(
            request,
            "reference/vendor_form.html",
            user=user,
            current_site=site,
            form_action="/reference/vendors/new",
            is_edit=False,
            error=e.message,
            form_data={"name": name},
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
    return render(
        request,
        "reference/vendor_form.html",
        user=user,
        current_site=site,
        form_action=f"/reference/vendors/{item_id}/edit",
        is_edit=True,
        form_data={"name": item.name},
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
        return render(
            request,
            "reference/vendor_form.html",
            user=user,
            current_site=site,
            form_action=f"/reference/vendors/{item_id}/edit",
            is_edit=True,
            error=e.message,
            form_data={"name": name},
        )
    return RedirectResponse("/reference/vendors", status_code=303)


@router.post("/vendors/{item_id}/delete")
def vendors_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    from urllib.parse import quote
    try:
        crud_vendor.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return RedirectResponse(
            f"/reference/vendors?error={quote(e.message)}",
            status_code=303,
        )
    return RedirectResponse("/reference/vendors", status_code=303)


# ============================================================
# Models (глобальные, только admin)
# ============================================================

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
        title="Models",
        add_url="/reference/models/new",
        edit_url_prefix="/reference/models/",
        delete_url_prefix="/reference/models/",
        columns=["Vendor", "Name"],
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
    return render(
        request,
        "reference/model_form.html",
        user=user,
        current_site=site,
        form_action="/reference/models/new",
        is_edit=False,
        form_data={},
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
    vendor_id = _to_int(form.get("vendor_id"))

    try:
        crud_model.create(db, vendor_id=vendor_id, name=name)
        db.commit()
    except ValidationError as e:
        db.rollback()
        vendors = crud_vendor.list_all(db)
        return render(
            request,
            "reference/model_form.html",
            user=user,
            current_site=site,
            form_action="/reference/models/new",
            is_edit=False,
            error=e.message,
            form_data={"name": name, "vendor_id": vendor_id or ""},
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
    return render(
        request,
        "reference/model_form.html",
        user=user,
        current_site=site,
        form_action=f"/reference/models/{item_id}/edit",
        is_edit=True,
        form_data={"name": item.name, "vendor_id": item.vendor_id},
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
    vendor_id = _to_int(form.get("vendor_id"))

    try:
        crud_model.update(db, model_id=item_id, vendor_id=vendor_id, name=name)
        db.commit()
    except ValidationError as e:
        db.rollback()
        vendors = crud_vendor.list_all(db)
        return render(
            request,
            "reference/model_form.html",
            user=user,
            current_site=site,
            form_action=f"/reference/models/{item_id}/edit",
            is_edit=True,
            error=e.message,
            form_data={"name": name, "vendor_id": vendor_id or ""},
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
    from urllib.parse import quote
    try:
        crud_model.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return RedirectResponse(
            f"/reference/models?error={quote(e.message)}",
            status_code=303,
        )
    return RedirectResponse("/reference/models", status_code=303)


# ============================================================
# Networks (привязаны к дому, доступны с правом Can edit)
# ============================================================

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
                x.gateway or "—",
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
        title="Networks",
        add_url="/reference/networks/new",
        edit_url_prefix="/reference/networks/",
        delete_url_prefix="/reference/networks/",
        columns=["Name", "Address", "Gateway", "VLAN"],
        rows=rows,
    )


@router.get("/networks/new", response_class=HTMLResponse)
def networks_new_form(
    request: Request,
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    return render(
        request,
        "reference/network_form.html",
        user=user,
        current_site=site,
        form_action="/reference/networks/new",
        is_edit=False,
        form_data={},
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
        return render(
            request,
            "reference/network_form.html",
            user=user,
            current_site=site,
            form_action="/reference/networks/new",
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
    return render(
        request,
        "reference/network_form.html",
        user=user,
        current_site=site,
        form_action=f"/reference/networks/{item_id}/edit",
        is_edit=True,
        form_data={
            "name": item.name,
            "network_address": item.network_address,
            "mask": item.mask,
            "gateway": item.gateway or "",
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
        return render(
            request,
            "reference/network_form.html",
            user=user,
            current_site=site,
            form_action=f"/reference/networks/{item_id}/edit",
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

    from urllib.parse import quote
    try:
        crud_network.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return RedirectResponse(
            f"/reference/networks?error={quote(e.message)}",
            status_code=303,
        )
    return RedirectResponse("/reference/networks", status_code=303)


# ============================================================
# Credential Types (глобальные, только admin)
# ============================================================

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
        title="Credential Types",
        add_url="/reference/credential-types/new",
        edit_url_prefix="/reference/credential-types/",
        delete_url_prefix="/reference/credential-types/",
        columns=["Name", "Description"],
        rows=rows,
    )


@router.get("/credential-types/new", response_class=HTMLResponse)
def credential_types_new_form(
    request: Request,
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    return render(
        request,
        "reference/credential_type_form.html",
        user=user,
        current_site=site,
        form_action="/reference/credential-types/new",
        is_edit=False,
        form_data={},
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
        return render(
            request,
            "reference/credential_type_form.html",
            user=user,
            current_site=site,
            form_action="/reference/credential-types/new",
            is_edit=False,
            error=e.message,
            form_data={"name": name, "description": description or ""},
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
    return render(
        request,
        "reference/credential_type_form.html",
        user=user,
        current_site=site,
        form_action=f"/reference/credential-types/{item_id}/edit",
        is_edit=True,
        form_data={"name": item.name, "description": item.description or ""},
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
        return render(
            request,
            "reference/credential_type_form.html",
            user=user,
            current_site=site,
            form_action=f"/reference/credential-types/{item_id}/edit",
            is_edit=True,
            error=e.message,
            form_data={"name": name, "description": description or ""},
        )
    return RedirectResponse("/reference/credential-types", status_code=303)


@router.post("/credential-types/{item_id}/delete")
def credential_types_delete(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    from urllib.parse import quote
    try:
        crud_cred_type.delete(db, item_id)
        db.commit()
    except ValidationError as e:
        db.rollback()
        return RedirectResponse(
            f"/reference/credential-types?error={quote(e.message)}",
            status_code=303,
        )
    return RedirectResponse("/reference/credential-types", status_code=303)


# ---------- Вспомогательное ----------

def _to_int(value) -> int | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _network_form_data(form) -> dict:
    return {
        "name": (form.get("name") or "").strip(),
        "network_address": (form.get("network_address") or "").strip(),
        "mask": (form.get("mask") or "").strip(),
        "gateway": (form.get("gateway") or "").strip() or None,
        "vlan": _to_int(form.get("vlan")),
        "description": (form.get("description") or "").strip() or None,
    }


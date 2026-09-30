from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_admin, require_edit, require_site
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.core.utils import redirect_with_error, to_int
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

def _ref_form(
    request,
    user,
    site,
    template,
    form_action,
    is_edit,
    form_data,
    error=None,
    **extra,
):
    return render(
        request,
        template,
        user=user,
        current_site=site,
        form_action=form_action,
        is_edit=is_edit,
        error=error,
        form_data=form_data,
        **extra,
    )


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
            "cells": [x.name, "✓" if x.is_active else "—", "✓" if x.supports_port_forwarding else "—", x.description or "—"],
        }
        for x in items
    ]
    return render(
        request,
        "reference/list.html",
        user=user,
        current_site=site,
        title_key="reference.title.device_types",
        add_url="/reference/device-types/new",
        edit_url_prefix="/reference/device-types/",
        delete_url_prefix="/reference/device-types/",
        column_keys=["devices.list.name", "devices.form.field.active", "reference.col.pf", "devices.form.field.description"],
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

    try:
        crud_device_type.create(db, name=name, is_active=is_active, supports_port_forwarding=supports_pf, description=description)
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
    supports_pf = form.get("supports_port_forwarding") == "on"
    description = (form.get("description") or "").strip() or None

    try:
        crud_device_type.update(
            db, type_id=item_id, name=name, is_active=is_active, supports_port_forwarding=supports_pf, description=description
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
        title_key="reference.title.networks",
        add_url="/reference/networks/new",
        edit_url_prefix="/reference/networks/",
        delete_url_prefix="/reference/networks/",
        column_keys=["devices.list.name", "reference.col.address", "devices.list.gateway", "reference.field.vlan"],
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

def _network_form_data(form) -> dict:
    return {
        "name": (form.get("name") or "").strip(),
        "network_address": (form.get("network_address") or "").strip(),
        "mask": (form.get("mask") or "").strip(),
        "gateway": (form.get("gateway") or "").strip() or None,
        "vlan": to_int(form.get("vlan")),
        "description": (form.get("description") or "").strip() or None,
    }

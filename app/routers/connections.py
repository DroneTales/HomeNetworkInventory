from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_admin, require_edit, require_site, require_user
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.crud import connection as crud_connection
from app.crud import device as crud_device
from app.database import get_db
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/connections", tags=["connections"])

@router.get("")
def list_connections(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    connections = crud_connection.list_all(db, site.id)
    warning = request.session.pop("warning", None)
    return render(
        request,
        "connections/list.html",
        user=user,
        current_site=site,
        connections=connections,
        warning=warning,
    )

@router.get("/new", response_class=HTMLResponse)
def new_connection_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    devices_payload = _devices_with_ports(db, site.id)
    return render(
        request,
        "connections/form.html",
        user=user,
        current_site=site,
        devices_payload=devices_payload,
        form_action="/connections/new",
        form_data={},
    )

@router.post("/new")
async def new_connection_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    form = await request.form()

    source_port_id = _to_int(form.get("source_port_id"))
    target_port_id = _to_int(form.get("target_port_id"))
    connection_type = (form.get("connection_type") or "physical").strip().lower()
    cable_type = (form.get("cable_type") or "").strip() or None
    description = (form.get("description") or "").strip() or None
    is_active = form.get("is_active") == "on"

    try:
        crud_connection.create(
            db,
            site_id=site.id,
            source_port_id=source_port_id,
            target_port_id=target_port_id,
            connection_type=connection_type,
            cable_type=cable_type,
            description=description,
            is_active=is_active,
        )
        db.commit()

    except ValidationError as e:
        db.rollback()
        devices_payload = _devices_with_ports(db, site.id)
        return render(
            request,
            "connections/form.html",
            user=user,
            current_site=site,
            devices_payload=devices_payload,
            form_action="/connections/new",
            error=e.message,
            form_data={
                "source_port_id": source_port_id or "",
                "target_port_id": target_port_id or "",
                "connection_type": connection_type,
                "cable_type": cable_type or "",
                "description": description or "",
                "is_active": is_active,
            },
        )

    return RedirectResponse("/connections", status_code=303)

@router.post("/{connection_id}/delete")
def delete_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    connection = crud_connection.get_by_id(db, connection_id, site_id=site.id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    crud_connection.delete(db, connection_id)
    db.commit()
    return RedirectResponse("/connections", status_code=303)

def _devices_with_ports(db: Session, site_id: int) -> list[dict]:
    devices = crud_device.list_all(db, site_id)
    payload = []
    for d in devices:
        ports = []
        for p in d.ports:
            ports.append({
                "id": p.id,
                "name": p.name,
                "interface_name": p.interface.name if p.interface else "",
            })
        if ports:
            payload.append({
                "id": d.id,
                "hostname": d.hostname,
                "ports": ports,
            })
    return payload

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

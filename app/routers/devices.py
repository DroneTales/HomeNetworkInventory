# Home Network Inventory
# Devices UI (list, view, form, sync logic).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.constants import (
    DHCP_POOL_TYPE_DYNAMIC,
    IFACE_TYPE_ETHERNET,
    IFACE_TYPE_PORT,
    IFACE_TYPE_WIFI,
    IFACE_TYPE_WIFI_AP,
    IP_TYPE_STATIC,
    PF_PROTOCOL_TCP,
    ROLE_ADMIN,
)
from app.core.deps import require_admin, require_edit, require_site, require_user
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.core.utils import parse_ipv4, to_int
from app.crud import connection as crud_connection
from app.crud import credential as crud_credential
from app.crud import credential_type as crud_cred_type
from app.crud import device as crud_device
from app.crud import device_type as crud_device_type
from app.crud import dhcp_pool as crud_dhcp
from app.crud import interface as crud_interface
from app.crud import ip_address as crud_ip
from app.crud import location as crud_location
from app.crud import network as crud_network
from app.crud import port as crud_port
from app.crud import port_forward as crud_pf
from app.crud import service as crud_service
from app.crud import vendor as crud_vendor
from app.crud import wifi_network as crud_wifi
from app.database import get_db
from app.models.device import Device
from app.models.dhcp_pool import DhcpPool
from app.models.interface import Interface
from app.models.site import Site
from app.models.user import User
from app.models.wifi_network import WiFiNetwork

router = APIRouter(prefix="/devices", tags=["devices"])

def _can_view_passwords(user: User) -> bool:
    return user.role == ROLE_ADMIN or user.can_view_passwords

def _can_change_passwords(user: User) -> bool:
    return user.role == ROLE_ADMIN or user.can_change_passwords

@router.get("")
def list_devices(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    devices = crud_device.list_all(db, site.id)

    def sort_key(d: Device) -> tuple:
        parsed = []
        for iface in d.interfaces:
            for ip in iface.ip_addresses:
                octets = parse_ipv4(ip.address)
                if octets is not None:
                    parsed.append(octets)
        if not parsed:
            return (1, (0, 0, 0, 0))
        return (0, min(parsed))

    devices.sort(key=sort_key)

    rows = []
    for d in devices:
        ips = []
        gateway = None
        for iface in d.interfaces:
            for ip in iface.ip_addresses:
                ips.append(ip)
                if gateway is None and ip.gateway:
                    gateway = ip.gateway

        rows.append({
            "device": d,
            "ips": ips,
            "gateway": gateway,
            "flags": {
                "dhcp": len(d.dhcp_pools) > 0,
                "ports": len(d.ports),
                "pf_out": len(d.port_forwards) > 0,
                "pf_in": len(d.port_forwards_targeted) > 0,
                "services": len(d.services),
            },
        })

    warning = request.session.pop("warning", None)

    return render(
        request,
        "devices/list.html",
        user=user,
        current_site=site,
        rows=rows,
        warning=warning,
    )

@router.get("/new", response_class=HTMLResponse)
def new_device_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    context = _form_context(db, site.id)
    context["interfaces"] = []
    context["can_view_passwords"] = True
    context["can_change_passwords"] = True
    return render(
        request,
        "devices/form.html",
        user=user,
        current_site=site,
        form_action="/devices/new",
        is_edit=False,
        **context,
    )

@router.post("/new")
async def new_device_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    form = await request.form()
    return _process_device_form(request, db, user, site, form, existing_device=None)

@router.get("/{device_id}", response_class=HTMLResponse)
def view_device(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    device = crud_device.get_by_id(db, device_id, site_id=site.id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    interfaces = crud_interface.list_by_device(db, device_id)
    ports = crud_port.list_by_device(db, device_id)
    wifi_networks = crud_wifi.list_by_device(db, device_id)
    dhcp_pools = crud_dhcp.list_by_device(db, device_id)
    connections = crud_connection.list_by_device(db, device_id)
    credentials = crud_credential.list_by_device(db, device_id)
    services = crud_service.list_by_device(db, device_id)
    port_forwards = crud_pf.list_by_device(db, device_id)

    device_ips = []
    for iface in interfaces:
        for ip in crud_ip.list_by_interface(db, iface.id):
            if ip.address:
                device_ips.append(ip.address)

    wifi_clients = []
    for w in wifi_networks:
        clients = []
        seen = set()
        for iface in w.connected_interfaces:
            cli_dev = iface.device
            if cli_dev is None or cli_dev.id == device_id or cli_dev.id in seen:
                continue
            seen.add(cli_dev.id)
            clients.append(cli_dev)
        clients.sort(key=lambda c: c.hostname.lower())
        if clients:
            wifi_clients.append({"wifi": w, "clients": clients})

    incoming_pfs = crud_pf.list_incoming(db, device_id, site.id, device_ips)
    incoming = []
    for pf in incoming_pfs:
        src_device = crud_device.get_by_id(db, pf.device_id, site_id=site.id)
        matched_ip = None
        if pf.internal_device_id is None and pf.internal_ip_manual:
            matched_ip = pf.internal_ip_manual
        incoming.append({
            "pf": pf,
            "source_device": src_device,
            "matched_ip": matched_ip,
        })

    return render(
        request,
        "devices/view.html",
        user=user,
        current_site=site,
        device=device,
        interfaces=interfaces,
        ports=ports,
        wifi_networks=wifi_networks,
        dhcp_pools=dhcp_pools,
        connections=connections,
        credentials=credentials,
        services=services,
        port_forwards=port_forwards,
        incoming_port_forwards=incoming,
        wifi_clients=wifi_clients,
    )

@router.get("/{device_id}/edit", response_class=HTMLResponse)
def edit_device_form(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    device = crud_device.get_by_id(db, device_id, site_id=site.id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    can_view = _can_view_passwords(user)
    can_change = _can_change_passwords(user)

    context = _form_context(db, site.id)
    context["interfaces"] = list(device.interfaces)
    context["can_view_passwords"] = can_view
    context["can_change_passwords"] = can_change

    form_data = _device_to_form_dict(device, show_passwords=can_view)

    return render(
        request,
        "devices/form.html",
        user=user,
        current_site=site,
        form_action=f"/devices/{device_id}/edit",
        is_edit=True,
        device_id=device_id,
        form_data=form_data,
        **context,
    )

@router.post("/{device_id}/edit")
async def edit_device_submit(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    device = crud_device.get_by_id(db, device_id, site_id=site.id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    form = await request.form()
    return _process_device_form(request, db, user, site, form, existing_device=device)

@router.post("/{device_id}/delete")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    site: Site = Depends(require_site),
):
    device = crud_device.get_by_id(db, device_id, site_id=site.id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    crud_device.delete(db, device_id)
    db.commit()
    return RedirectResponse("/devices", status_code=303)

def _process_device_form(
    request: Request,
    db: Session,
    user: User,
    site: Site,
    form,
    existing_device: Device | None,
):
    hostname = (form.get("hostname") or "").strip()
    human_readable_name = (form.get("human_readable_name") or "").strip() or None
    remarks = (form.get("remarks") or "").strip() or None
    device_type_id = to_int(form.get("device_type_id"))
    vendor_id = to_int(form.get("vendor_id"))
    model_id = to_int(form.get("model_id"))
    location_id = to_int(form.get("location_id"))
    network_id = to_int(form.get("network_id"))
    is_active = form.get("is_active") == "on"

    interfaces = _collect_interfaces(form)
    ports = _collect_ports(form)
    wifi_networks = _collect_wifi_networks(form)
    dhcp_pools = _collect_dhcp_pools(form)
    credentials = _collect_credentials(form)
    services = _collect_services(form)
    port_forwards = _collect_port_forwards(form)

    is_edit = existing_device is not None
    form_action = (
        f"/devices/{existing_device.id}/edit" if is_edit else "/devices/new"
    )
    device_id = existing_device.id if is_edit else None

    can_view = _can_view_passwords(user)
    can_change = _can_change_passwords(user)

    try:
        if is_edit:
            device = crud_device.update(
                db,
                device_id=existing_device.id,
                hostname=hostname,
                human_readable_name=human_readable_name,
                remarks=remarks,
                device_type_id=device_type_id,
                vendor_id=vendor_id,
                model_id=model_id,
                location_id=location_id,
                network_id=network_id,
                is_active=is_active,
            )
        else:
            device = crud_device.create(
                db,
                site_id=site.id,
                hostname=hostname,
                human_readable_name=human_readable_name,
                remarks=remarks,
                device_type_id=device_type_id,
                vendor_id=vendor_id,
                model_id=model_id,
                location_id=location_id,
                network_id=network_id,
                is_active=is_active,
            )

        created_ips, iface_id_map, deferred_links, ifaces_to_delete = _sync_interfaces(
            db, device, interfaces, network_id
        )
        wifi_map = _sync_wifi_networks(db, device, wifi_networks, iface_id_map)
        _apply_client_wifi_links(db, deferred_links, wifi_map)
        _check_deletable_interfaces(db, ifaces_to_delete)
        for iface_id in ifaces_to_delete:
            crud_interface.delete(db, iface_id)
        _sync_ports(db, device, ports)
        _sync_dhcp_pools(db, device, dhcp_pools)
        _sync_credentials(db, device, credentials)
        _sync_services(db, device, services)
        _sync_port_forwards(db, device, port_forwards)

        crud_device.validate_full(db, device)
        db.commit()

    except ValidationError as e:
        db.rollback()
        context = _form_context(db, site.id)
        if is_edit:
            device_reloaded = crud_device.get_by_id(db, existing_device.id, site_id=site.id)
            context["interfaces"] = list(device_reloaded.interfaces) if device_reloaded else []
        else:
            context["interfaces"] = []
        context["can_view_passwords"] = can_view
        context["can_change_passwords"] = can_change

        return render(
            request,
            "devices/form.html",
            user=user,
            current_site=site,
            form_action=form_action,
            is_edit=is_edit,
            device_id=device_id,
            error=e.message,
            form_data=_form_dict(form),
            **context,
        )

    warning = _check_dhcp_conflicts(db, created_ips, site_id=site.id)
    if warning:
        request.session["warning"] = warning

    return RedirectResponse("/devices", status_code=303)

# _sync_* helpers reconcile submitted form rows with existing children:
# rows with an "id" are updated, rows without are created, rows missing
# from the submission are deleted. The pattern is shared by all _sync_* below.
def _sync_wifi_networks(
    db: Session,
    device: Device,
    items: list[dict],
    iface_id_map: dict[int, int] | None = None,
) -> dict[int, int]:
    wifi_map: dict[int, int] = {}
    existing = {w.id: w for w in device.wifi_networks}
    seen_ids = set()
    iface_id_map = iface_id_map or {}

    for idx, data in enumerate(items):
        item_id = data.get("id")
        interface_id = _resolve_iface_id(data.get("interface_id"), iface_id_map)
        if item_id and item_id in existing:
            wifi = existing[item_id]
            password = data.get("password")
            if not password:
                password = wifi.password
            crud_wifi.update(
                db,
                wifi_id=item_id,
                ssid=data["ssid"],
                interface_id=interface_id,
                encryption=data["encryption"],
                password=password,
                is_guest=data["is_guest"],
            )
            seen_ids.add(item_id)
            wifi_map[idx] = item_id
        else:
            wifi = crud_wifi.create(
                db,
                device_id=device.id,
                ssid=data["ssid"],
                interface_id=interface_id,
                encryption=data["encryption"],
                password=data["password"],
                is_guest=data["is_guest"],
            )
            wifi_map[idx] = wifi.id

    for wifi_id, wifi in existing.items():
        if wifi_id not in seen_ids:
            db.delete(wifi)
    db.flush()

    return wifi_map

def _sync_interfaces(
    db: Session,
    device: Device,
    items: list[dict],
    network_id: int | None,
) -> tuple[list[tuple[str, str]], dict[int, int], list[tuple[int, str]], list[int]]:
    existing = {i.id: i for i in device.interfaces}
    seen_ids = set()
    all_ips: list[tuple[str, str]] = []
    iface_id_map: dict[int, int] = {}
    deferred_links: list[tuple[int, str]] = []

    for idx, data in enumerate(items):
        item_id = data.get("id")
        is_wifi_client = data["type"] == IFACE_TYPE_WIFI

        if item_id and item_id in existing:
            iface = existing[item_id]
            crud_interface.update(
                db,
                interface_id=item_id,
                name=data["name"],
                type=data["type"],
                mac=data["mac"],
                band=data.get("band"),
                connected_wifi_network_id=iface.connected_wifi_network_id if is_wifi_client else None,
                defer_wifi_validation=is_wifi_client,
            )
            seen_ids.add(item_id)
        else:
            iface = crud_interface.create(
                db,
                device_id=device.id,
                name=data["name"],
                type=data["type"],
                mac=data["mac"],
                band=data.get("band"),
                connected_wifi_network_id=None,
                defer_wifi_validation=is_wifi_client,
            )

        iface_id_map[idx] = iface.id

        if is_wifi_client:
            raw = data.get("connected_wifi_network_id")
            if raw:
                deferred_links.append((iface.id, str(raw).strip()))

        existing_ips = {ip.id: ip for ip in iface.ip_addresses}
        # Always attempt to create/update the IP record (except for port);
        # required-ness of the address is enforced inside crud_ip.validate
        needs_ip_record = data["type"] != IFACE_TYPE_PORT

        if needs_ip_record:
            if existing_ips:
                first_id = next(iter(existing_ips))
                crud_ip.update(
                    db,
                    ip_id=first_id,
                    interface_id=iface.id,
                    address=data.get("address"),
                    mask=data.get("mask"),
                    address_type=data["address_type"],
                    gateway=data.get("gateway"),
                    dns=data.get("dns"),
                    network_id=network_id,
                )
                for extra_id in list(existing_ips.keys())[1:]:
                    db.delete(existing_ips[extra_id])
            else:
                crud_ip.create(
                    db,
                    interface_id=iface.id,
                    address=data.get("address"),
                    mask=data.get("mask"),
                    address_type=data["address_type"],
                    gateway=data.get("gateway"),
                    dns=data.get("dns"),
                    network_id=network_id,
                )
            if data.get("address"):
                all_ips.append((data["address"], data["address_type"]))
        else:
            for ip in existing_ips.values():
                db.delete(ip)

    to_delete = [iface.id for iface_id, iface in existing.items() if iface_id not in seen_ids]

    return all_ips, iface_id_map, deferred_links, to_delete

def _check_deletable_interfaces(db: Session, iface_ids: list[int]) -> None:
    for iface_id in iface_ids:
        iface = db.get(Interface, iface_id)
        if iface is None or iface.type != IFACE_TYPE_WIFI_AP:
            continue
        linked = (
            db.query(WiFiNetwork)
            .filter(WiFiNetwork.interface_id == iface_id)
            .count()
        )
        if linked:
            raise ValidationError(
                f"Cannot delete Wi-Fi AP interface '{iface.name}' while Wi-Fi networks are broadcast through it",
                field="interface_id",
            )


def _apply_client_wifi_links(
    db: Session,
    deferred_links: list[tuple[int, str]],
    wifi_map: dict[int, int],
) -> None:
    for iface_id, raw in deferred_links:
        wifi_id = _resolve_wifi_id(raw, wifi_map)
        iface = db.get(Interface, iface_id)
        if iface is not None:
            iface.connected_wifi_network_id = wifi_id
    db.flush()


def _sync_ports(db: Session, device: Device, items: list[dict]) -> None:
    valid_interface_ids = {
        row[0]
        for row in db.query(Interface.id)
        .filter(Interface.device_id == device.id)
        .all()
    }

    existing = {p.id: p for p in device.ports}
    seen_ids = set()

    for data in items:
        item_id = data.get("id")
        interface_id = data.get("interface_id")

        if interface_id is None or interface_id not in valid_interface_ids:
            continue

        if item_id and item_id in existing:
            crud_port.update(
                db,
                port_id=item_id,
                interface_id=interface_id,
                name=data["name"],
                description=data["description"],
            )
            seen_ids.add(item_id)
        else:
            crud_port.create(
                db,
                device_id=device.id,
                interface_id=interface_id,
                name=data["name"],
                description=data["description"],
            )

    for port_id, port in existing.items():
        if port_id not in seen_ids:
            db.delete(port)
    db.flush()

def _sync_dhcp_pools(db: Session, device: Device, items: list[dict]) -> None:
    existing = {p.id: p for p in device.dhcp_pools}
    seen_ids = set()

    for data in items:
        item_id = data.get("id")
        if item_id and item_id in existing:
            crud_dhcp.update(
                db,
                pool_id=item_id,
                name=data["name"],
                type=data["type"],
                start_ip=data["start_ip"],
                end_ip=data["end_ip"],
                gateway=data["gateway"],
                dns=data["dns"],
                description=data["description"],
            )
            seen_ids.add(item_id)
        else:
            crud_dhcp.create(
                db,
                device_id=device.id,
                start_ip=data["start_ip"],
                end_ip=data["end_ip"],
                type=data["type"],
                name=data["name"],
                gateway=data["gateway"],
                dns=data["dns"],
                description=data["description"],
            )

    for pool_id, pool in existing.items():
        if pool_id not in seen_ids:
            db.delete(pool)
    db.flush()

def _sync_credentials(db: Session, device: Device, items: list[dict]) -> None:
    existing = {c.id: c for c in device.credentials}
    seen_ids = set()

    for data in items:
        item_id = data.get("id")
        if item_id and item_id in existing:
            cred = existing[item_id]
            password = data.get("password")
            if not password:
                password = cred.password
            crud_credential.update(
                db,
                credential_id=item_id,
                type_id=data["type_id"],
                username=data["username"],
                password=password,
                description=data["description"],
            )
            seen_ids.add(item_id)
        else:
            crud_credential.create(
                db,
                device_id=device.id,
                type_id=data["type_id"],
                username=data["username"],
                password=data["password"],
                description=data["description"],
            )

    for cred_id, cred in existing.items():
        if cred_id not in seen_ids:
            db.delete(cred)
    db.flush()

def _sync_services(db: Session, device: Device, items: list[dict]) -> None:
    existing = {s.id: s for s in device.services}
    seen_ids = set()

    for data in items:
        item_id = data.get("id")
        if item_id and item_id in existing:
            crud_service.update(
                db,
                service_id=item_id,
                name=data["name"],
                protocol=data["protocol"],
                port=data["port"],
                url=data["url"],
                path=data["path"],
                description=data["description"],
            )
            seen_ids.add(item_id)
        else:
            crud_service.create(
                db,
                device_id=device.id,
                name=data["name"],
                protocol=data["protocol"],
                port=data["port"],
                url=data["url"],
                path=data["path"],
                description=data["description"],
            )

    for svc_id, svc in existing.items():
        if svc_id not in seen_ids:
            db.delete(svc)
    db.flush()

def _form_context(db: Session, site_id: int) -> dict:
    return {
        "device_types": crud_device_type.list_all(db),
        "vendors": crud_vendor.list_all(db),
        "locations": crud_location.list_all(db, site_id),
        "networks": crud_network.list_all(db, site_id),
        "all_wifi_networks": crud_wifi.list_by_site(db, site_id),
        "credential_types": crud_cred_type.list_all(db),
        "all_devices": crud_device.list_all(db, site_id),
    }

def _device_to_form_dict(device: Device, show_passwords: bool = True) -> dict:
    interfaces = []
    for iface in device.interfaces:
        ip = iface.ip_addresses[0] if iface.ip_addresses else None
        interfaces.append({
            "id": iface.id,
            "name": iface.name,
            "type": iface.type,
            "mac": iface.mac or "",
            "band": iface.band or "",
            "address": ip.address if ip else "",
            "mask": ip.mask if ip else "255.255.255.0",
            "address_type": ip.address_type if ip else IP_TYPE_STATIC,
            "gateway": (ip.gateway if ip and ip.gateway else "") or "",
            "dns": (ip.dns if ip and ip.dns else "") or "",
            "connected_wifi_network_id": iface.connected_wifi_network_id or "",
        })

    ports = []
    for p in device.ports:
        ports.append({
            "id": p.id,
            "name": p.name,
            "interface_id": p.interface_id,
            "description": p.description or "",
        })

    wifi_networks = []
    for w in device.wifi_networks:
        wifi_networks.append({
            "id": w.id,
            "ssid": w.ssid,
            "interface_id": w.interface_id or "",
            "encryption": w.encryption or "",
            "password": (w.password or "") if show_passwords else "",
            "is_guest": w.is_guest,
        })

    dhcp_pools = []
    for p in device.dhcp_pools:
        dhcp_pools.append({
            "id": p.id,
            "name": p.name or "",
            "type": p.type,
            "start_ip": p.start_ip,
            "end_ip": p.end_ip,
            "gateway": p.gateway or "",
            "dns": p.dns or "",
            "description": p.description or "",
        })

    credentials = []
    for c in device.credentials:
        credentials.append({
            "id": c.id,
            "type_id": c.type_id or "",
            "username": c.username or "",
            "password": (c.password or "") if show_passwords else "",
            "description": c.description or "",
        })

    services = []
    for s in device.services:
        services.append({
            "id": s.id,
            "name": s.name,
            "protocol": s.protocol or "",
            "port": s.port if s.port is not None else "",
            "url": s.url or "",
            "path": s.path or "",
            "description": s.description or "",
        })

    port_forwards = []
    for pf in device.port_forwards:
        port_forwards.append({
            "id": pf.id,
            "external_port_start": pf.external_port_start,
            "external_port_end": pf.external_port_end,
            "protocol": pf.protocol,
            "internal_device_id": pf.internal_device_id or "",
            "internal_ip_manual": pf.internal_ip_manual or "",
            "internal_port_start": pf.internal_port_start,
            "internal_port_end": pf.internal_port_end,
            "description": pf.description or "",
            "is_active": pf.is_active,
        })

    return {
        "hostname": device.hostname,
        "human_readable_name": device.human_readable_name or "",
        "remarks": device.remarks or "",
        "device_type_id": device.device_type_id or "",
        "vendor_id": device.vendor_id or "",
        "model_id": device.model_id or "",
        "location_id": device.location_id or "",
        "network_id": device.network_id or "",
        "is_active": device.is_active,
        "interfaces": interfaces,
        "ports": ports,
        "wifi_networks": wifi_networks,
        "dhcp_pools": dhcp_pools,
        "credentials": credentials,
        "services": services,
        "port_forwards": port_forwards,
    }

def _form_dict(form) -> dict:
    return {
        "hostname": form.get("hostname") or "",
        "human_readable_name": form.get("human_readable_name") or "",
        "remarks": form.get("remarks") or "",
        "device_type_id": form.get("device_type_id") or "",
        "vendor_id": form.get("vendor_id") or "",
        "model_id": form.get("model_id") or "",
        "location_id": form.get("location_id") or "",
        "network_id": form.get("network_id") or "",
        "is_active": form.get("is_active") == "on",
        "interfaces": _collect_interfaces(form),
        "ports": _collect_ports(form),
        "wifi_networks": _collect_wifi_networks(form),
        "dhcp_pools": _collect_dhcp_pools(form),
        "credentials": _collect_credentials(form),
        "services": _collect_services(form),
        "port_forwards": _collect_port_forwards(form),
    }

def _resolve_iface_id(value, iface_id_map: dict[int, int]) -> int | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.startswith("new:"):
        try:
            idx = int(value[4:])
        except ValueError:
            return None
        return iface_id_map.get(idx)
    try:
        return int(value)
    except ValueError:
        return None

def _resolve_wifi_id(value, wifi_map: dict[int, int]) -> int | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.startswith("new:"):
        try:
            idx = int(value[4:])
        except ValueError:
            return None
        return wifi_map.get(idx)
    try:
        return int(value)
    except ValueError:
        return None

def _collect_interfaces(form) -> list[dict]:
    ids = form.getlist("interface_id")
    names = form.getlist("interface_name")
    types = form.getlist("interface_type")
    macs = form.getlist("interface_mac")
    bands = form.getlist("interface_band")
    addresses = form.getlist("interface_address")
    masks = form.getlist("interface_mask")
    address_types = form.getlist("interface_address_type")
    gateways = form.getlist("interface_gateway")
    dns_list = form.getlist("interface_dns")
    wifi_links = form.getlist("interface_connected_wifi")

    result = []
    for i, name in enumerate(names):
        name = (name or "").strip()
        if not name:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        iface_type = (types[i] if i < len(types) else IFACE_TYPE_ETHERNET).strip().lower()
        mac = (macs[i] if i < len(macs) else "").strip() or None
        band = (bands[i] if i < len(bands) else "").strip() or None

        address = (addresses[i] if i < len(addresses) else "").strip() or None
        mask = (masks[i] if i < len(masks) else "").strip() or None
        address_type = (address_types[i] if i < len(address_types) else IP_TYPE_STATIC).strip().lower()
        gateway = (gateways[i] if i < len(gateways) else "").strip() or None
        dns = (dns_list[i] if i < len(dns_list) else "").strip() or None
        connected_wifi = (wifi_links[i] if i < len(wifi_links) else "").strip() or None

        result.append({
            "id": item_id,
            "name": name,
            "type": iface_type,
            "mac": mac,
            "band": band,
            "address": address,
            "mask": mask,
            "address_type": address_type,
            "gateway": gateway,
            "dns": dns,
            "connected_wifi_network_id": connected_wifi,
        })

    return result

def _collect_ports(form) -> list[dict]:
    ids = form.getlist("port_id")
    names = form.getlist("port_name")
    interface_ids = form.getlist("port_interface_id")
    descriptions = form.getlist("port_description")

    result = []
    for i, name in enumerate(names):
        name = (name or "").strip()
        if not name:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        interface_id = to_int(interface_ids[i] if i < len(interface_ids) else None)
        description = (descriptions[i] if i < len(descriptions) else "").strip() or None

        result.append({
            "id": item_id,
            "name": name,
            "interface_id": interface_id,
            "description": description,
        })

    return result

def _collect_wifi_networks(form) -> list[dict]:
    ids = form.getlist("wifi_id")
    ssids = form.getlist("wifi_ssid")
    iface_ids = form.getlist("wifi_interface_id")
    encryptions = form.getlist("wifi_encryption")
    passwords = form.getlist("wifi_password")
    guests = form.getlist("wifi_is_guest")

    result = []
    for i, ssid in enumerate(ssids):
        ssid = (ssid or "").strip()
        if not ssid:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        interface_id = (iface_ids[i] if i < len(iface_ids) else "").strip() or None
        encryption = (encryptions[i] if i < len(encryptions) else "").strip() or None
        password = (passwords[i] if i < len(passwords) else "").strip() or None
        guest = (guests[i] if i < len(guests) else "") == "on"

        result.append({
            "id": item_id,
            "ssid": ssid,
            "interface_id": interface_id,
            "encryption": encryption,
            "password": password,
            "is_guest": guest,
        })

    return result

def _collect_dhcp_pools(form) -> list[dict]:
    ids = form.getlist("dhcp_id")
    names = form.getlist("dhcp_name")
    types = form.getlist("dhcp_type")
    starts = form.getlist("dhcp_start_ip")
    ends = form.getlist("dhcp_end_ip")
    gateways = form.getlist("dhcp_gateway")
    dns_list = form.getlist("dhcp_dns")
    descriptions = form.getlist("dhcp_description")

    result = []
    for i, start in enumerate(starts):
        start = (start or "").strip()
        end = (ends[i] if i < len(ends) else "").strip()
        if not start and not end:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        result.append({
            "id": item_id,
            "name": (names[i] if i < len(names) else "").strip() or None,
            "type": (types[i] if i < len(types) else DHCP_POOL_TYPE_DYNAMIC).strip().lower(),
            "start_ip": start,
            "end_ip": end,
            "gateway": (gateways[i] if i < len(gateways) else "").strip() or None,
            "dns": (dns_list[i] if i < len(dns_list) else "").strip() or None,
            "description": (descriptions[i] if i < len(descriptions) else "").strip() or None,
        })

    return result

def _collect_credentials(form) -> list[dict]:
    ids = form.getlist("credential_id")
    type_ids = form.getlist("credential_type_id")
    usernames = form.getlist("credential_username")
    passwords = form.getlist("credential_password")
    descriptions = form.getlist("credential_description")

    result = []
    max_len = max(len(usernames), len(passwords), len(type_ids), len(ids))

    for i in range(max_len):
        item_id = to_int(ids[i] if i < len(ids) else None)
        type_id = to_int(type_ids[i] if i < len(type_ids) else None)
        username = (usernames[i] if i < len(usernames) else "").strip() or None
        password = (passwords[i] if i < len(passwords) else "").strip() or None
        description = (descriptions[i] if i < len(descriptions) else "").strip() or None

        if type_id is None and username is None and password is None:
            continue

        result.append({
            "id": item_id,
            "type_id": type_id,
            "username": username,
            "password": password,
            "description": description,
        })

    return result

def _collect_services(form) -> list[dict]:
    ids = form.getlist("service_id")
    names = form.getlist("service_name")
    protocols = form.getlist("service_protocol")
    ports = form.getlist("service_port")
    urls = form.getlist("service_url")
    paths = form.getlist("service_path")
    descriptions = form.getlist("service_description")

    result = []
    for i, name in enumerate(names):
        name = (name or "").strip()
        if not name:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        protocol = (protocols[i] if i < len(protocols) else "").strip() or None
        port = to_int(ports[i] if i < len(ports) else None)
        url = (urls[i] if i < len(urls) else "").strip() or None
        path = (paths[i] if i < len(paths) else "").strip() or None
        description = (descriptions[i] if i < len(descriptions) else "").strip() or None

        result.append({
            "id": item_id,
            "name": name,
            "protocol": protocol,
            "port": port,
            "url": url,
            "path": path,
            "description": description,
        })

    return result

def _check_dhcp_conflicts(
    db: Session,
    ips: list[tuple[str, str]],
    site_id: int,
) -> str | None:
    if not ips:
        return None

    pools = (
        db.query(DhcpPool)
        .join(Device, DhcpPool.device_id == Device.id)
        .filter(Device.site_id == site_id)
        .all()
    )
    conflicts = []
    for ip, address_type in ips:
        if address_type != IP_TYPE_STATIC:
            continue
        for pool in pools:
            from app.core.validation import is_ip_in_range
            if is_ip_in_range(ip, pool.start_ip, pool.end_ip):
                pool_name = pool.name or f"pool #{pool.id}"
                conflicts.append(
                    f"IP {ip} falls into DHCP pool '{pool_name}' "
                    f"({pool.start_ip}-{pool.end_ip})"
                )
    if conflicts:
        return "Saved. " + "; ".join(conflicts)
    return None


def _collect_port_forwards(form) -> list[dict]:
    ids = form.getlist("pf_id")
    ext_starts = form.getlist("pf_external_start")
    ext_ends = form.getlist("pf_external_end")
    protocols = form.getlist("pf_protocol")
    target_types = form.getlist("pf_target_type")
    internal_device_ids = form.getlist("pf_internal_device_id")
    internal_ip_manual_list = form.getlist("pf_internal_ip_manual")
    internal_starts = form.getlist("pf_internal_start")
    internal_ends = form.getlist("pf_internal_end")
    descriptions = form.getlist("pf_description")

    active_flags = set()
    for idx, v in enumerate(form.getlist("pf_is_active")):
        if v == "on":
            active_flags.add(idx)
    active_by_id = {}
    for idx, item_id in enumerate(ids):
        if item_id and item_id.strip() and idx in active_flags:
            active_by_id[item_id.strip()] = True

    max_len = max(len(ext_starts), len(ids))
    result = []
    for i in range(max_len):
        ext_start = (ext_starts[i] if i < len(ext_starts) else "").strip()
        ext_end = (ext_ends[i] if i < len(ext_ends) else "").strip()
        if not ext_start and not ext_end:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        target_type = (target_types[i] if i < len(target_types) else "device").strip().lower()
        internal_device_id = to_int(internal_device_ids[i] if i < len(internal_device_ids) else None)
        internal_ip_manual = (internal_ip_manual_list[i] if i < len(internal_ip_manual_list) else "").strip() or None

        if target_type == "ip":
            internal_device_id = None
        else:
            internal_ip_manual = None

        is_active = (
            active_by_id.get(str(item_id), False) if item_id else i in active_flags
        )

        result.append({
            "id": item_id,
            "external_port_start": ext_start,
            "external_port_end": ext_end,
            "protocol": (protocols[i] if i < len(protocols) else PF_PROTOCOL_TCP).strip().lower(),
            "internal_device_id": internal_device_id,
            "internal_ip_manual": internal_ip_manual,
            "internal_port_start": (internal_starts[i] if i < len(internal_starts) else "").strip(),
            "internal_port_end": (internal_ends[i] if i < len(internal_ends) else "").strip(),
            "description": (descriptions[i] if i < len(descriptions) else "").strip() or None,
            "is_active": is_active,
        })
    return result


def _sync_port_forwards(db: Session, device: Device, items: list[dict]) -> None:
    existing = {pf.id: pf for pf in device.port_forwards}
    seen_ids = set()

    for data in items:
        item_id = data.get("id")
        if item_id and item_id in existing:
            crud_pf.update(
                db,
                pf_id=item_id,
                external_port_start=data["external_port_start"],
                external_port_end=data["external_port_end"],
                protocol=data["protocol"],
                internal_device_id=data["internal_device_id"],
                internal_ip_manual=data["internal_ip_manual"],
                internal_port_start=data["internal_port_start"],
                internal_port_end=data["internal_port_end"],
                description=data["description"],
                is_active=data["is_active"],
            )
            seen_ids.add(item_id)
        else:
            crud_pf.create(
                db,
                device_id=device.id,
                external_port_start=data["external_port_start"],
                external_port_end=data["external_port_end"],
                protocol=data["protocol"],
                internal_device_id=data["internal_device_id"],
                internal_ip_manual=data["internal_ip_manual"],
                internal_port_start=data["internal_port_start"],
                internal_port_end=data["internal_port_end"],
                description=data["description"],
                is_active=data["is_active"],
            )

    for pf_id, pf in existing.items():
        if pf_id not in seen_ids:
            db.delete(pf)
    db.flush()

# Home Network Inventory
# Devices UI: device create/edit form.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.constants import IP_TYPE_STATIC, VALID_SERVICE_PROTOCOLS
from app.core.deps import require_edit, require_site
from app.core.exceptions import ValidationError
from app.core.templating import render
from app.core.utils import to_int
from app.crud import credential_type as crud_cred_type, device as crud_device, device_type as crud_device_type, interface as crud_interface, location as crud_location, mac_filter as crud_mac_filter, network as crud_network, vendor as crud_vendor, wifi_network as crud_wifi
from app.database import get_db
from app.models.device import Device
from app.models.site import Site
from app.models.user import User
from app.routers.devices.base import _can_view_passwords, _can_change_passwords, _device_mac_for_wifi
from app.routers.devices.form_collect import _collect_interfaces, _collect_ports, _collect_wifi_networks, _collect_dhcp_pools, _collect_credentials, _collect_services, _collect_port_forwards
from app.routers.devices.form_sync import _sync_wifi_networks, _sync_interfaces, _sync_ports, _sync_dhcp_pools, _sync_credentials, _sync_services, _sync_port_forwards, _apply_client_wifi_links, _check_deletable_interfaces, _check_dhcp_conflicts
from app.routers.devices.base import router

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

    form_data = _device_to_form_dict(db, device, show_passwords=can_view)

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
    description = (form.get("description") or "").strip() or None
    remarks = (form.get("remarks") or "").strip() or None
    device_type_id = to_int(form.get("device_type_id"))
    vendor_id = to_int(form.get("vendor_id"))
    model_id = to_int(form.get("model_id"))
    location_id = to_int(form.get("location_id"))
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
                description=description,
                remarks=remarks,
                device_type_id=device_type_id,
                vendor_id=vendor_id,
                model_id=model_id,
                location_id=location_id,
                is_active=is_active,
            )
        else:
            device = crud_device.create(
                db,
                site_id=site.id,
                hostname=hostname,
                human_readable_name=human_readable_name,
                description=description,
                remarks=remarks,
                device_type_id=device_type_id,
                vendor_id=vendor_id,
                model_id=model_id,
                location_id=location_id,
                is_active=is_active,
            )

        created_ips, iface_id_map, deferred_links, ifaces_to_delete = _sync_interfaces(
            db, device, interfaces
        )
        wifi_map = _sync_wifi_networks(db, device, wifi_networks, iface_id_map)
        _apply_client_wifi_links(db, deferred_links, wifi_map)
        _check_deletable_interfaces(db, ifaces_to_delete)
        for iface_id in ifaces_to_delete:
            crud_interface.delete(db, iface_id)
        _sync_ports(db, device, ports, iface_id_map)
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

def _form_context(db: Session, site_id: int) -> dict:
    return {
        "device_types": crud_device_type.list_all(db),
        "vendors": crud_vendor.list_all(db),
        "locations": crud_location.list_all(db, site_id),
        "networks": crud_network.list_all(db, site_id),
        "all_wifi_networks": crud_wifi.list_by_site(db, site_id),
        "credential_types": crud_cred_type.list_all(db),
        "all_devices": crud_device.list_all(db, site_id),
        "service_protocols": sorted(VALID_SERVICE_PROTOCOLS),
    }

def _device_to_form_dict(db: Session, device: Device, show_passwords: bool = True) -> dict:
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
            "network_id": iface.network_id or "",
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
        mac_entries = []
        for mf in w.mac_filters:
            dev = mf.device
            mac_entries.append({
                "id": mf.id,
                "device_id": mf.device_id,
                "device_name": dev.human_readable_name if dev else "",
                "mac": _device_mac_for_wifi(dev, w.id),
                "is_active": mf.is_active,
            })
        eligible = crud_mac_filter.eligible_devices(db, w.id)
        eligible_data = [
            {"id": e["device"].id, "hostname": e["device"].hostname, "human_readable_name": e["device"].human_readable_name, "mac": e["mac"]}
            for e in eligible
        ]
        wifi_networks.append({
            "id": w.id,
            "ssid": w.ssid,
            "interface_id": w.interface_id or "",
            "encryption": w.encryption or "",
            "password": (w.password or "") if show_passwords else "",
            "is_guest": w.is_guest,
            "mac_filter": w.mac_filter or 0,
            "mac_filter_entries": mac_entries,
            "eligible_devices": eligible_data,
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
            "url": s.url or "",
            "username": s.username or "",
            "password": (s.password or "") if show_passwords else "",
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
            "nat_loopback": pf.nat_loopback,
        })

    return {
        "hostname": device.hostname,
        "human_readable_name": device.human_readable_name or "",
        "description": device.description or "",
        "remarks": device.remarks or "",
        "device_type_id": device.device_type_id or "",
        "vendor_id": device.vendor_id or "",
        "model_id": device.model_id or "",
        "location_id": device.location_id or "",
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
        "description": form.get("description") or "",
        "remarks": form.get("remarks") or "",
        "device_type_id": form.get("device_type_id") or "",
        "vendor_id": form.get("vendor_id") or "",
        "model_id": form.get("model_id") or "",
        "location_id": form.get("location_id") or "",
        "is_active": form.get("is_active") == "on",
        "interfaces": _collect_interfaces(form),
        "ports": _collect_ports(form),
        "wifi_networks": _collect_wifi_networks(form),
        "dhcp_pools": _collect_dhcp_pools(form),
        "credentials": _collect_credentials(form),
        "services": _collect_services(form),
        "port_forwards": _collect_port_forwards(form),
    }

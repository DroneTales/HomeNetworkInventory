from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_admin, require_edit, require_site, require_user
from app.core.exceptions import ValidationError
from app.core.templating import render
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
from app.crud import service as crud_service
from app.crud import vendor as crud_vendor
from app.crud import wifi_network as crud_wifi
from app.database import get_db
from app.models.device import Device
from app.models.interface import Interface
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/devices", tags=["devices"])


def _can_view_passwords(user: User) -> bool:
    return user.role == "admin" or user.can_view_passwords


def _can_change_passwords(user: User) -> bool:
    return user.role == "admin" or user.can_change_passwords


# ---------- Список устройств ----------

@router.get("")
def list_devices(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    devices = crud_device.list_all(db, site.id)

    def sort_key(d: Device) -> tuple:
        ips = []
        for iface in d.interfaces:
            for ip in iface.ip_addresses:
                ips.append(ip.address)
        if not ips:
            return (1, "")
        return (0, min(ips))

    devices.sort(key=sort_key)

    rows = []
    for d in devices:
        primary_ip = None
        for iface in d.interfaces:
            for ip in iface.ip_addresses:
                primary_ip = ip
                break
            if primary_ip:
                break

        rows.append({"device": d, "primary_ip": primary_ip})

    warning = request.session.pop("warning", None)

    return render(
        request,
        "devices/list.html",
        user=user,
        current_site=site,
        rows=rows,
        warning=warning,
    )


# ---------- Форма создания ----------

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


# ---------- Карточка ----------

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
    )


# ---------- Редактирование ----------

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


# ---------- Удаление ----------

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


# ---------- Общая логика создания/обновления ----------

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
    device_type_id = _to_int(form.get("device_type_id"))
    vendor_id = _to_int(form.get("vendor_id"))
    model_id = _to_int(form.get("model_id"))
    location_id = _to_int(form.get("location_id"))
    network_id = _to_int(form.get("network_id"))
    is_active = form.get("is_active") == "on"

    interfaces = _collect_interfaces(form)
    ports = _collect_ports(form)
    wifi_networks = _collect_wifi_networks(form)
    dhcp_pools = _collect_dhcp_pools(form)
    credentials = _collect_credentials(form)
    services = _collect_services(form)

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

        wifi_map = _sync_wifi_networks(db, device, wifi_networks)
        created_ips = _sync_interfaces(db, device, interfaces, wifi_map, network_id)
        _sync_ports(db, device, ports)
        _sync_dhcp_pools(db, device, dhcp_pools)
        _sync_credentials(db, device, credentials)
        _sync_services(db, device, services)

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

    warning = _check_dhcp_conflicts(db, created_ips)
    if warning:
        request.session["warning"] = warning

    return RedirectResponse("/devices", status_code=303)


# ---------- Синхронизация детей ----------

def _sync_wifi_networks(db: Session, device: Device, items: list[dict]) -> dict[int, int]:
    wifi_map: dict[int, int] = {}
    existing = {w.id: w for w in device.wifi_networks}
    seen_ids = set()

    for idx, data in enumerate(items):
        item_id = data.get("id")
        if item_id and item_id in existing:
            wifi = existing[item_id]
            password = data.get("password")
            if not password:
                password = wifi.password
            crud_wifi.update(
                db,
                wifi_id=item_id,
                ssid=data["ssid"],
                band=data["band"],
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
                band=data["band"],
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
    wifi_map: dict[int, int],
    network_id: int | None,
) -> list[tuple[str, str]]:
    existing = {i.id: i for i in device.interfaces}
    seen_ids = set()
    all_ips: list[tuple[str, str]] = []

    for data in items:
        item_id = data.get("id")
        connected_id = None
        if data["type"] == "wifi":
            connected_id = _resolve_wifi_id(data.get("connected_wifi_network_id"), wifi_map)

        if item_id and item_id in existing:
            iface = existing[item_id]
            crud_interface.update(
                db,
                interface_id=item_id,
                name=data["name"],
                type=data["type"],
                mac=data["mac"],
                connected_wifi_network_id=connected_id,
            )
            seen_ids.add(item_id)
        else:
            iface = crud_interface.create(
                db,
                device_id=device.id,
                name=data["name"],
                type=data["type"],
                mac=data["mac"],
                connected_wifi_network_id=connected_id,
            )

        existing_ips = {ip.id: ip for ip in iface.ip_addresses}
        if data.get("address"):
            if existing_ips:
                first_id = next(iter(existing_ips))
                crud_ip.update(
                    db,
                    ip_id=first_id,
                    interface_id=iface.id,
                    address=data["address"],
                    mask=data["mask"],
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
                    address=data["address"],
                    mask=data["mask"],
                    address_type=data["address_type"],
                    gateway=data.get("gateway"),
                    dns=data.get("dns"),
                    network_id=network_id,
                )
            all_ips.append((data["address"], data["address_type"]))
        else:
            for ip in existing_ips.values():
                db.delete(ip)

    for iface_id, iface in existing.items():
        if iface_id not in seen_ids:
            db.delete(iface)
    db.flush()

    return all_ips


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


# ---------- Вспомогательные ----------

def _form_context(db: Session, site_id: int) -> dict:
    return {
        "device_types": crud_device_type.list_all(db),
        "vendors": crud_vendor.list_all(db),
        "locations": crud_location.list_all(db, site_id),
        "networks": crud_network.list_all(db, site_id),
        "all_wifi_networks": crud_wifi.list_all(db),
        "credential_types": crud_cred_type.list_all(db),
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
            "address": ip.address if ip else "",
            "mask": ip.mask if ip else "255.255.255.0",
            "address_type": ip.address_type if ip else "static",
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
            "band": w.band or "",
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
    }


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

        item_id = _to_int(ids[i] if i < len(ids) else None)
        iface_type = (types[i] if i < len(types) else "ethernet").strip().lower()
        mac = (macs[i] if i < len(macs) else "").strip() or None

        address = (addresses[i] if i < len(addresses) else "").strip() or None
        mask = (masks[i] if i < len(masks) else "").strip() or None
        address_type = (address_types[i] if i < len(address_types) else "static").strip().lower()
        gateway = (gateways[i] if i < len(gateways) else "").strip() or None
        dns = (dns_list[i] if i < len(dns_list) else "").strip() or None
        connected_wifi = (wifi_links[i] if i < len(wifi_links) else "").strip() or None

        result.append({
            "id": item_id,
            "name": name,
            "type": iface_type,
            "mac": mac,
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

        item_id = _to_int(ids[i] if i < len(ids) else None)
        interface_id = _to_int(interface_ids[i] if i < len(interface_ids) else None)
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
    bands = form.getlist("wifi_band")
    encryptions = form.getlist("wifi_encryption")
    passwords = form.getlist("wifi_password")
    guests = form.getlist("wifi_is_guest")

    result = []
    for i, ssid in enumerate(ssids):
        ssid = (ssid or "").strip()
        if not ssid:
            continue

        item_id = _to_int(ids[i] if i < len(ids) else None)
        band = (bands[i] if i < len(bands) else "").strip() or None
        encryption = (encryptions[i] if i < len(encryptions) else "").strip() or None
        password = (passwords[i] if i < len(passwords) else "").strip() or None
        guest = (guests[i] if i < len(guests) else "") == "on"

        result.append({
            "id": item_id,
            "ssid": ssid,
            "band": band,
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

        item_id = _to_int(ids[i] if i < len(ids) else None)
        result.append({
            "id": item_id,
            "name": (names[i] if i < len(names) else "").strip() or None,
            "type": (types[i] if i < len(types) else "dynamic").strip().lower(),
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
        item_id = _to_int(ids[i] if i < len(ids) else None)
        type_id = _to_int(type_ids[i] if i < len(type_ids) else None)
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

        item_id = _to_int(ids[i] if i < len(ids) else None)
        protocol = (protocols[i] if i < len(protocols) else "").strip() or None
        port = _to_int(ports[i] if i < len(ports) else None)
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


def _check_dhcp_conflicts(db: Session, ips: list[tuple[str, str]]) -> str | None:
    if not ips:
        return None

    all_pools = crud_dhcp.list_all(db)
    conflicts = []
    for ip, address_type in ips:
        if address_type != "static":
            continue
        for pool in all_pools:
            from app.core.validation import is_ip_in_range
            if is_ip_in_range(ip, pool.start_ip, pool.end_ip):
                pool_name = pool.name or f"pool #{pool.id}"
                conflicts.append(
                    f"IP {ip} falls into DHCP pool '{pool_name}' "
                    f"({pool.start_ip}–{pool.end_ip})"
                )
    if conflicts:
        return "Saved. " + "; ".join(conflicts)
    return None


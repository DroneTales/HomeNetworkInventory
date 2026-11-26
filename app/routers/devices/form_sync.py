# Home Network Inventory
# Devices UI: relation sync helpers.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.orm import Session
from app.core.constants import IFACE_TYPE_PORT, IFACE_TYPE_WIFI, IFACE_TYPE_WIFI_AP, IP_TYPE_STATIC
from app.core.exceptions import ValidationError
from app.crud import credential as crud_credential, dhcp_pool as crud_dhcp, interface as crud_interface, ip_address as crud_ip, mac_filter as crud_mac_filter, port as crud_port, port_forward as crud_pf, service as crud_service, wifi_network as crud_wifi
from app.models.device import Device
from app.models.dhcp_pool import DhcpPool
from app.models.interface import Interface
from app.models.wifi_network import WiFiNetwork

def _sync_mac_filters(db: Session, wifi, entries: list[dict]) -> None:
    existing = {mf.id: mf for mf in wifi.mac_filters}
    seen = set()
    for entry in entries:
        device_id = entry.get("device")
        if not device_id:
            continue
        fid = entry.get("id")
        active = bool(entry.get("active", True))
        if fid and fid in existing:
            existing[fid].is_active = active
            seen.add(fid)
        else:
            mf = crud_mac_filter.create(
                db,
                wifi_network_id=wifi.id,
                device_id=device_id,
                is_active=active,
            )
            seen.add(mf.id)
    for fid, mf in existing.items():
        if fid not in seen:
            db.delete(mf)
    db.flush()

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
                mac_filter=data.get("mac_filter", 0),
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
                mac_filter=data.get("mac_filter", 0),
            )
            wifi_map[idx] = wifi.id

        _sync_mac_filters(db, wifi, data.get("mac_filters") or [])

    for wifi_id, wifi in existing.items():
        if wifi_id not in seen_ids:
            db.delete(wifi)
    db.flush()

    return wifi_map

def _sync_interfaces(
    db: Session,
    device: Device,
    items: list[dict],
) -> tuple[list[tuple[str, str]], dict[int, int], list[tuple[int, str]], list[int]]:
    existing = {i.id: i for i in device.interfaces}
    seen_ids = set()
    all_ips: list[tuple[str, str]] = []
    iface_id_map: dict[int, int] = {}
    deferred_links: list[tuple[int, str]] = []

    for idx, data in enumerate(items):
        item_id = data.get("id")
        is_wifi_client = data["type"] == IFACE_TYPE_WIFI
        iface_network_id = data.get("network_id")

        if item_id and item_id in existing:
            iface = existing[item_id]
            crud_interface.update(
                db,
                interface_id=item_id,
                name=data["name"],
                type=data["type"],
                mac=data["mac"],
                band=data.get("band"),
                connected_wifi_network_id=None,
                network_id=iface_network_id,
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
                network_id=iface_network_id,
                defer_wifi_validation=is_wifi_client,
            )

        iface_id_map[idx] = iface.id

        if is_wifi_client:
            raw = data.get("connected_wifi_network_id") or ""
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
        if iface is None:
            continue
        if wifi_id is None:
            raise ValidationError(
                "Wi-Fi interface must be connected to a Wi-Fi network",
                field="connected_wifi_network_id",
            )
        iface.connected_wifi_network_id = wifi_id
    db.flush()

def _sync_ports(
    db: Session,
    device: Device,
    items: list[dict],
    iface_id_map: dict[int, int],
) -> None:
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
        interface_id = _resolve_iface_id(data.get("interface_id"), iface_id_map)

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
                url=data["url"],
                username=data.get("username"),
                password=data.get("password"),
                description=data["description"],
            )
            seen_ids.add(item_id)
        else:
            crud_service.create(
                db,
                device_id=device.id,
                name=data["name"],
                protocol=data["protocol"],
                url=data["url"],
                username=data.get("username"),
                password=data.get("password"),
                description=data["description"],
            )

    for svc_id, svc in existing.items():
        if svc_id not in seen_ids:
            db.delete(svc)
    db.flush()

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
                nat_loopback=data["nat_loopback"],
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
                nat_loopback=data["nat_loopback"],
            )

    for pf_id, pf in existing.items():
        if pf_id not in seen_ids:
            db.delete(pf)
    db.flush()

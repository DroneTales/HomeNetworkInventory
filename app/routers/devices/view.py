# Home Network Inventory
# Devices UI: device view and delete.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.deps import require_admin, require_site, require_user
from app.core.templating import render
from app.crud import connection as crud_connection, credential as crud_credential, device as crud_device, dhcp_pool as crud_dhcp, interface as crud_interface, port as crud_port, port_forward as crud_pf, service as crud_service, wifi_network as crud_wifi
from app.database import get_db
from app.models.device import Device
from app.models.site import Site
from app.models.user import User
from app.routers.devices.base import _ip_to_int, _device_mac_for_wifi
from app.routers.devices.base import router

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

    all_devices = crud_device.list_all(db, site.id)
    all_dhcp_clients = []
    all_reserved_entries = []
    for dev in all_devices:
        for iface in dev.interfaces:
            for ip in iface.ip_addresses:
                if not ip.address:
                    continue
                entry = {"device": dev, "interface": iface, "ip": ip}
                if ip.address_type == "dhcp":
                    all_dhcp_clients.append(entry)
                elif ip.address_type == "reserved":
                    all_reserved_entries.append(entry)

    def _ip_sort_key(entry):
        v = _ip_to_int(entry["ip"].address)
        return (0, v) if v is not None else (1, 0)

    def _mac_sort_key(entry):
        mac = (entry["interface"].mac or "").strip().lower()
        return (1, "") if not mac else (0, mac)

    all_dhcp_clients.sort(key=_mac_sort_key)
    all_reserved_entries.sort(key=_ip_sort_key)
    wifi_networks = crud_wifi.list_by_device(db, device_id)
    dhcp_pools = crud_dhcp.list_by_device(db, device_id)
    connections = crud_connection.list_by_device(db, device_id)
    credentials = crud_credential.list_by_device(db, device_id)
    services = crud_service.list_by_device(db, device_id)
    port_forwards = crud_pf.list_by_device(db, device_id)

    device_ips = []
    for iface in interfaces:
        for ip in iface.ip_addresses:
            if ip.address:
                device_ips.append(ip.address)

    conn_by_port: dict[int, tuple] = {}
    for c in connections:
        conn_by_port[c.source_port_id] = (c, "outgoing")
        conn_by_port.setdefault(c.target_port_id, (c, "incoming"))

    port_rows = []
    for p in ports:
        conn_info = conn_by_port.get(p.id)
        conn = conn_info[0] if conn_info else None
        direction = conn_info[1] if conn_info else None
        port_rows.append({
            "port": p,
            "connection": conn,
            "direction": direction,
        })

    iface_groups_map: dict[int | None, dict] = {}
    for iface in interfaces:
        key = iface.network_id
        if key not in iface_groups_map:
            iface_groups_map[key] = {
                "network": iface.network if key else None,
                "interfaces": [],
            }
        iface_groups_map[key]["interfaces"].append(iface)

    interface_groups = sorted(
        [g for g in iface_groups_map.values() if g["network"] is not None],
        key=lambda g: g["network"].name,
    )
    no_network = iface_groups_map.get(None)
    if no_network:
        interface_groups.append(no_network)

    dhcp_pools_payload = []
    for pool in dhcp_pools:
        clients = []
        if pool.type == "fixed":
            lo = _ip_to_int(pool.start_ip)
            hi = _ip_to_int(pool.end_ip)
            if lo is not None and hi is not None and lo <= hi:
                for entry in all_reserved_entries:
                    v = _ip_to_int(entry["ip"].address)
                    if v is not None and lo <= v <= hi:
                        clients.append(entry)
        dhcp_pools_payload.append({"pool": pool, "clients": clients})

    dhcp_pools_payload.sort(key=lambda x: (0 if x["pool"].type == "fixed" else 1, x["pool"].start_ip or ""))

    dhcp_dynamic_clients = all_dhcp_clients

    wifi_rows = []
    for w in wifi_networks:
        clients = []
        seen = set()
        for iface in w.connected_interfaces:
            cli_dev = iface.device
            if cli_dev is None or cli_dev.id == device_id or cli_dev.id in seen:
                continue
            seen.add(cli_dev.id)
            ip = iface.ip_addresses[0] if iface.ip_addresses else None
            clients.append({"device": cli_dev, "interface": iface, "ip": ip})
        in_filter = {mf.device_id for mf in w.mac_filters if mf.is_active}
        _mode = w.mac_filter or 0
        for c in clients:
            dev_id = c["device"].id
            if _mode == 1:
                c["gray"] = dev_id not in in_filter
            elif _mode == 2:
                c["gray"] = dev_id in in_filter
            else:
                c["gray"] = False
        clients.sort(key=lambda c: (c["gray"], (c["device"].hostname or "").lower()))
        mac_entries = []
        for mf in w.mac_filters:
            dev = mf.device
            mac_entries.append({
                "filter": mf,
                "device": dev,
                "mac": _device_mac_for_wifi(dev, w.id),
            })
        wifi_rows.append({"wifi": w, "clients": clients, "mac_filters": mac_entries})

    incoming_pfs = crud_pf.list_incoming(db, device_id, site.id, device_ips)
    incoming = []
    for pf in incoming_pfs:
        matched_ip = None
        if pf.internal_device_id is None and pf.internal_ip_manual:
            matched_ip = pf.internal_ip_manual
        incoming.append({
            "pf": pf,
            "source_device": pf.device,
            "matched_ip": matched_ip,
        })

    return render(
        request,
        "devices/view.html",
        user=user,
        current_site=site,
        device=device,
        interfaces=interfaces,
        interface_groups=interface_groups,
        ports=ports,
        port_rows=port_rows,
        wifi_networks=wifi_networks,
        dhcp_pools=dhcp_pools,
        dhcp_pools_payload=dhcp_pools_payload,
        dhcp_dynamic_clients=dhcp_dynamic_clients,
        credentials=credentials,
        services=services,
        port_forwards=port_forwards,
        incoming_port_forwards=incoming,
        wifi_rows=wifi_rows,
    )

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

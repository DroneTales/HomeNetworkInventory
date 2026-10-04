# Home Network Inventory
# Topology graph data.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import require_edit, require_site, require_user
from app.core.device_classify import classify_device
from app.core.templating import render
from app.crud import device as crud_device
from app.crud import topology_position as crud_pos
from app.database import get_db
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/topology", tags=["topology"])

@router.get("", response_class=HTMLResponse)
def topology_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    return render(
        request,
        "topology/index.html",
        user=user,
        current_site=site,
    )


@router.get("/data")
def topology_data(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    devices = crud_device.list_all(db, site.id)

    nodes = []
    port_nodes = []

    for d in devices:
        ports_count = len(d.ports)
        has_wifi = len(d.wifi_networks) > 0
        is_wifi_client = any(
            iface.connected_wifi_network_id is not None
            for iface in d.interfaces
        )

        wifi_ssids = [w.ssid for w in d.wifi_networks if w.ssid]
        wifi_client_ssids = []
        for iface in d.interfaces:
            if iface.connected_wifi_network and iface.connected_wifi_network.ssid:
                ssid = iface.connected_wifi_network.ssid
                if ssid not in wifi_client_ssids:
                    wifi_client_ssids.append(ssid)

        category, icon = classify_device(d)

        # Prefer the IP flagged as primary; otherwise fall back to the
        # first non-empty address on any interface
        primary_ip = None
        for iface in d.interfaces:
            for ip in iface.ip_addresses:
                if ip.is_primary and ip.address:
                    primary_ip = ip.address
                    break
            if primary_ip:
                break
        if not primary_ip:
            for iface in d.interfaces:
                for ip in iface.ip_addresses:
                    if ip.address:
                        primary_ip = ip.address
                        break
                if primary_ip:
                    break

        macs = [iface.mac for iface in d.interfaces if iface.mac]

        nodes.append({
            "id": f"device-{d.id}",
            "device_id": d.id,
            "label": d.hostname,
            "human_name": d.human_readable_name or "",
            "location_id": d.location_id,
            "category": category,
            "icon": icon,
            "ip": primary_ip or "",
            "mac": macs[0] if macs else "",
            "ports_count": ports_count,
            "has_wifi": has_wifi,
            "is_wifi_client": is_wifi_client,
            "wifi_ssids": wifi_ssids,
            "wifi_client_ssids": wifi_client_ssids,
            "has_services": len(d.services) > 0,
            "is_active": d.is_active,
        })

        for p in d.ports:
            port_nodes.append({
                "id": f"port-{p.id}",
                "port_id": p.id,
                "device_id": d.id,
                "label": p.name,
                "interface_name": p.interface.name if p.interface else "",
            })

    # Edges come from outgoing connections only; a symmetric connection
    # row already covers both ports, so iterating incoming would duplicate
    edges = []
    for d in devices:
        for p in d.ports:
            for c in p.connections_from:
                if c.target_port is None:
                    continue
                edges.append({
                    "id": f"conn-{c.id}",
                    "source": f"port-{c.source_port_id}",
                    "target": f"port-{c.target_port_id}",
                    "type": c.connection_type,
                    "cable": c.cable_type or "",
                    "is_active": c.is_active,
                })

    # Only locations that actually contain devices are emitted,
    # so the graph never renders empty compound nodes
    locations = {}
    for d in devices:
        if d.location:
            locations[d.location.id] = {"id": d.location.id, "name": d.location.name}

    positions = [
        {"device_id": row.device_id, "x": row.x, "y": row.y}
        for row in crud_pos.list_by_site(db, site.id)
    ]

    return JSONResponse({
        "site": {"id": site.id, "name": site.name},
        "locations": list(locations.values()),
        "devices": nodes,
        "ports": port_nodes,
        "edges": edges,
        "positions": positions,
    })

@router.post("/positions")
async def save_positions(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    payload = await request.json()
    positions = payload.get("positions") or []
    updated = crud_pos.upsert_many(db, site.id, positions)
    db.commit()
    return JSONResponse({"ok": True, "updated": updated})


@router.delete("/positions")
def reset_positions(
    db: Session = Depends(get_db),
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    deleted = crud_pos.clear_site(db, site.id)
    db.commit()
    return JSONResponse({"ok": True, "deleted": deleted})

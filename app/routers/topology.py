from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import require_site, require_user
from app.core.templating import render
from app.crud import device as crud_device
from app.database import get_db
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/topology", tags=["topology"])

ICON_MODEM = "fa-tower-broadcast"
ICON_HUB = "fa-circle-nodes"
ICON_WIFI = "fa-wifi"
ICON_ROUTER = "fa-router"
ICON_CAMERA = "fa-video"
ICON_VIDEO_SERVER = "fa-clapperboard"
ICON_SERVER = "fa-server"
ICON_OTHER = "fa-plug"


def _classify(device, ports_count: int, has_external_ip: bool,
              has_wifi: bool, has_rtsp: bool, has_other_service: bool) -> tuple[str, str]:
    if has_external_ip:
        return "modem", ICON_MODEM
    if device.device_type and not device.device_type.is_active and ports_count > 1:
        return "hub", ICON_HUB
    if has_wifi and ports_count > 1:
        return "wifi_router", ICON_WIFI
    if has_wifi:
        return "wifi_ap", ICON_WIFI
    if ports_count > 1:
        return "router", ICON_ROUTER
    if has_rtsp and not has_other_service:
        return "camera", ICON_CAMERA
    if has_rtsp and has_other_service:
        return "video_server", ICON_VIDEO_SERVER
    if has_other_service:
        return "server", ICON_SERVER
    return "other", ICON_OTHER


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
        has_external_ip = any(
            ip.address_type == "external"
            for iface in d.interfaces
            for ip in iface.ip_addresses
        )
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

        has_rtsp = False
        has_other_service = False
        for svc in d.services:
            proto = (svc.protocol or "").lower()
            if proto == "rtsp":
                has_rtsp = True
            elif proto and proto != "ssh":
                has_other_service = True

        category, icon = _classify(
            d, ports_count, has_external_ip, has_wifi,
            has_rtsp, has_other_service,
        )

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

    locations = {}
    for d in devices:
        if d.location:
            locations[d.location.id] = {"id": d.location.id, "name": d.location.name}

    return JSONResponse({
        "site": {"id": site.id, "name": site.name},
        "locations": list(locations.values()),
        "devices": nodes,
        "ports": port_nodes,
        "edges": edges,
    })

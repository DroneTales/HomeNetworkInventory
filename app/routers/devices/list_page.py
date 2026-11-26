# Home Network Inventory
# Devices UI: device list.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Depends, Request
from sqlalchemy.orm import Session
from app.core.constants import IFACE_TYPE_WIFI_AP
from app.core.deps import require_site, require_user
from app.core.templating import render
from app.core.utils import parse_ipv4
from app.crud import device as crud_device
from app.database import get_db
from app.models.device import Device
from app.models.site import Site
from app.models.user import User
from app.routers.devices.base import router

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
        lines = []
        for iface in d.interfaces:
            if iface.ip_addresses:
                for ip in iface.ip_addresses:
                    ips.append(ip)
                    if gateway is None and ip.gateway:
                        gateway = ip.gateway
                    lines.append({
                        "ip": ip.address,
                        "ip_type": ip.address_type,
                        "gateway": ip.gateway,
                        "mac": iface.mac,
                        "iface_type": iface.type,
                        "iface_name": iface.name,
                    })
            elif iface.mac:
                lines.append({
                    "ip": None,
                    "ip_type": None,
                    "gateway": None,
                    "mac": iface.mac,
                    "iface_type": iface.type,
                    "iface_name": iface.name,
                })

        device_label = " ".join(
            part for part in (
                d.vendor.name if d.vendor else "",
                d.model.name if d.model else "",
            ) if part
        )

        rows.append({
            "device": d,
            "ips": ips,
            "gateway": gateway,
            "lines": lines,
            "device_label": device_label,
            "flags": {
                "dhcp": len(d.dhcp_pools) > 0,
                "ports": len(d.ports),
                "pf_out": len(d.port_forwards) > 0,
                "pf_in": len(d.port_forwards_targeted) > 0,
                "services": len(d.services),
                "wifi_ap": any(i.type == IFACE_TYPE_WIFI_AP for i in d.interfaces),
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

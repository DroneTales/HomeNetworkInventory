# Home Network Inventory
# Device classification by type (icons and categories).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.constants import IP_TYPE_EXTERNAL

ICON_MODEM = "fa-tower-broadcast"
ICON_HUB = "fa-circle-nodes"
ICON_WIFI = "fa-wifi"
ICON_ROUTER = "fa-router"
ICON_CAMERA = "fa-video"
ICON_VIDEO_SERVER = "fa-clapperboard"
ICON_SERVER = "fa-server"
ICON_OTHER = "fa-plug"


def classify_device(device) -> tuple[str, str]:
    ports_count = len(device.ports)
    has_external_ip = any(
        ip.address_type == IP_TYPE_EXTERNAL
        for iface in device.interfaces
        for ip in iface.ip_addresses
    )
    has_wifi = len(device.wifi_networks) > 0

    has_rtsp = False
    has_other_service = False
    for svc in device.services:
        proto = (svc.protocol or "").lower()
        if proto == "rtsp":
            has_rtsp = True
        elif proto and proto != "ssh":
            has_other_service = True

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

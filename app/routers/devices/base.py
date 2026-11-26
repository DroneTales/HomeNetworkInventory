# Home Network Inventory
# Devices UI: shared router and helpers.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter

from app.core.constants import ROLE_ADMIN
from app.models.user import User

router = APIRouter(prefix="/devices", tags=["devices"])

def _ip_to_int(ip: str | None) -> int | None:
    if not ip:
        return None
    parts = ip.split(".")
    if len(parts) != 4:
        return None
    n = 0
    for part in parts:
        try:
            v = int(part)
        except ValueError:
            return None
        if v < 0 or v > 255:
            return None
        n = (n << 8) | v
    return n

def _can_view_passwords(user: User) -> bool:
    return user.role == ROLE_ADMIN or user.can_view_passwords

def _can_change_passwords(user: User) -> bool:
    return user.role == ROLE_ADMIN or user.can_change_passwords

def _slug(value: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in value.lower()).strip("_") or "site"

def _device_mac_for_wifi(device, wifi_id: int) -> str:
    if device is None:
        return ""
    for iface in device.interfaces:
        if iface.connected_wifi_network_id == wifi_id and iface.mac:
            return iface.mac
    return ""

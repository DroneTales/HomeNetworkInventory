# Home Network Inventory
# MAC filter CRUD (per-SSID allow/deny lists).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.validation import require_found
from app.models.device import Device
from app.models.mac_filter import MacFilter
from app.models.wifi_network import WiFiNetwork


def list_by_wifi(db: Session, wifi_network_id: int) -> list[MacFilter]:
    return (
        db.query(MacFilter)
        .filter(MacFilter.wifi_network_id == wifi_network_id)
        .order_by(MacFilter.id)
        .all()
    )


def get_by_id(db: Session, filter_id: int) -> MacFilter | None:
    return db.get(MacFilter, filter_id)


def create(
    db: Session,
    wifi_network_id: int,
    device_id: int,
    is_active: bool = True,
) -> MacFilter:
    require_found(db.get(WiFiNetwork, wifi_network_id), "Wi-Fi network", field="wifi_network_id")
    require_found(db.get(Device, device_id), "Device", field="device_id")

    existing = (
        db.query(MacFilter)
        .filter(
            MacFilter.wifi_network_id == wifi_network_id,
            MacFilter.device_id == device_id,
        )
        .first()
    )
    if existing is not None:
        raise ValidationError("Device is already in this MAC filter", field="device_id")

    mf = MacFilter(
        wifi_network_id=wifi_network_id,
        device_id=device_id,
        is_active=is_active,
    )
    db.add(mf)
    db.flush()
    return mf


def delete(db: Session, filter_id: int) -> None:
    mf = db.get(MacFilter, filter_id)
    if mf is not None:
        db.delete(mf)
        db.flush()


def eligible_devices(db: Session, wifi_network_id: int) -> list[dict]:
    """Devices connected to this SSID (via a wifi interface) that have a MAC
    and are not yet present in the filter."""
    wifi = db.get(WiFiNetwork, wifi_network_id)
    if wifi is None:
        return []
    already = {mf.device_id for mf in list_by_wifi(db, wifi_network_id)}
    result: list[dict] = []
    seen = set()
    for iface in wifi.connected_interfaces:
        dev = iface.device
        if dev is None or dev.id in seen or dev.id in already:
            continue
        mac = (iface.mac or "").strip()
        if not mac:
            continue
        seen.add(dev.id)
        result.append({"device": dev, "interface": iface, "mac": mac})
    result.sort(key=lambda x: (x["device"].hostname or "").lower())
    return result

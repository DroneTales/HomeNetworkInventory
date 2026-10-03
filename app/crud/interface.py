# Home Network Inventory
# Device interfaces CRUD with MAC uniqueness.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.orm import Session

from app.core.constants import IFACE_TYPE_WIFI, VALID_IFACE_TYPES
from app.core.exceptions import ValidationError
from app.core.validation import require_found, validate_choice, validate_mac
from app.models.device import Device
from app.models.interface import Interface
from app.models.wifi_network import WiFiNetwork


def list_by_device(db: Session, device_id: int) -> list[Interface]:
    return (
        db.query(Interface)
        .filter(Interface.device_id == device_id)
        .order_by(Interface.name)
        .all()
    )

def get_by_id(db: Session, interface_id: int) -> Interface | None:
    return db.get(Interface, interface_id)

def _check_mac_unique(
    db: Session,
    mac: str | None,
    exclude_id: int | None = None,
) -> None:
    # MAC addresses are unique globally (across all sites)
    if not mac:
        return

    query = db.query(Interface).filter(Interface.mac == mac)
    if exclude_id is not None:
        query = query.filter(Interface.id != exclude_id)

    if query.first() is not None:
        raise ValidationError(f"MAC address '{mac}' already exists", field="mac")

def create(
    db: Session,
    device_id: int,
    name: str,
    type: str,
    mac: str | None = None,
    is_active: bool = True,
    connected_wifi_network_id: int | None = None,
) -> Interface:
    require_found(db.get(Device, device_id), "Device", field="device_id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    type = validate_choice(
        (type or "").strip().lower(), VALID_IFACE_TYPES, "interface type", "type"
    )

    if mac is not None and mac.strip():
        mac = validate_mac(mac, field="mac")
        _check_mac_unique(db, mac)
    else:
        mac = None

    if type == IFACE_TYPE_WIFI and connected_wifi_network_id is None:
        raise ValidationError(
            "Wi-Fi interface must be connected to a Wi-Fi network",
            field="connected_wifi_network_id",
        )

    if connected_wifi_network_id is not None:
        if type != IFACE_TYPE_WIFI:
            raise ValidationError(
                "Only Wi-Fi interfaces can be connected to a Wi-Fi network",
                field="connected_wifi_network_id",
            )
        require_found(
            db.get(WiFiNetwork, connected_wifi_network_id),
            "Wi-Fi network",
            field="connected_wifi_network_id",
        )

    iface = Interface(
        device_id=device_id,
        name=name,
        type=type,
        mac=mac,
        is_active=is_active,
        connected_wifi_network_id=connected_wifi_network_id,
    )
    db.add(iface)
    db.flush()
    return iface

def update(
    db: Session,
    interface_id: int,
    name: str,
    type: str,
    mac: str | None = None,
    is_active: bool = True,
    connected_wifi_network_id: int | None = None,
) -> Interface:
    iface = require_found(get_by_id(db, interface_id), "Interface")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    type = validate_choice(
        (type or "").strip().lower(), VALID_IFACE_TYPES, "interface type", "type"
    )

    if mac is not None and mac.strip():
        mac = validate_mac(mac, field="mac")
        _check_mac_unique(db, mac, exclude_id=interface_id)
    else:
        mac = None

    if type == IFACE_TYPE_WIFI and connected_wifi_network_id is None:
        raise ValidationError(
            "Wi-Fi interface must be connected to a Wi-Fi network",
            field="connected_wifi_network_id",
        )

    if connected_wifi_network_id is not None:
        if type != IFACE_TYPE_WIFI:
            raise ValidationError(
                "Only Wi-Fi interfaces can be connected to a Wi-Fi network",
                field="connected_wifi_network_id",
            )
        require_found(
            db.get(WiFiNetwork, connected_wifi_network_id),
            "Wi-Fi network",
            field="connected_wifi_network_id",
        )

    iface.name = name
    iface.type = type
    iface.mac = mac
    iface.is_active = is_active
    iface.connected_wifi_network_id = connected_wifi_network_id
    db.flush()
    return iface

def delete(db: Session, interface_id: int) -> None:
    iface = get_by_id(db, interface_id)
    if iface is None:
        return

    from app.models.port import Port
    db.query(Port).filter(Port.interface_id == interface_id).delete(synchronize_session=False)

    db.delete(iface)
    db.flush()

# Home Network Inventory
# Device interfaces CRUD with MAC uniqueness.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.orm import Session

from app.core.constants import (
    IFACE_TYPE_PORT,
    IFACE_TYPE_WIFI,
    IFACE_TYPE_WIFI_AP,
    VALID_BANDS,
    VALID_IFACE_TYPES,
)
from app.core.exceptions import ValidationError
from app.core.validation import require_found, validate_choice, validate_mac
from app.models.device import Device
from app.models.interface import Interface
from app.models.network import Network
from app.models.wifi_network import WiFiNetwork


def _validate_band(type: str, band: str | None) -> str | None:
    band = (band or "").strip() or None

    if type == IFACE_TYPE_WIFI_AP:
        if band not in VALID_BANDS:
            raise ValidationError(
                "Band is required for Wi-Fi AP interface (2.4, 5 or 6)",
                field="band",
            )
        return band

    if band is not None:
        raise ValidationError(
            "Band is only allowed for Wi-Fi AP interface",
            field="band",
        )
    return None


def _validate_wifi_links(
    type: str,
    band: str | None,
    connected_wifi_network_id: int | None,
    db: Session,
    defer_wifi_validation: bool = False,
) -> None:
    if not defer_wifi_validation and type == IFACE_TYPE_WIFI and connected_wifi_network_id is None:
        raise ValidationError(
            "Wi-Fi interface must be connected to a Wi-Fi network",
            field="connected_wifi_network_id",
        )

    if type == IFACE_TYPE_WIFI_AP:
        if connected_wifi_network_id is not None:
            raise ValidationError(
                "Wi-Fi AP interface cannot be connected to a Wi-Fi network",
                field="connected_wifi_network_id",
            )
        return

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


def _validate_network(
    db: Session,
    type: str,
    network_id: int | None,
    site_id: int,
) -> int | None:
    if type == IFACE_TYPE_PORT:
        if network_id is not None:
            raise ValidationError(
                "Port interface cannot belong to a network",
                field="network_id",
            )
        return None

    if network_id is None:
        return None

    network = require_found(db.get(Network, network_id), "Network", field="network_id")
    if network.site_id != site_id:
        raise ValidationError(
            "Network belongs to another home",
            field="network_id",
        )
    return network_id

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
    band: str | None = None,
    is_active: bool = True,
    connected_wifi_network_id: int | None = None,
    network_id: int | None = None,
    defer_wifi_validation: bool = False,
) -> Interface:
    device = require_found(db.get(Device, device_id), "Device", field="device_id")

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

    band = _validate_band(type, band)
    _validate_wifi_links(type, band, connected_wifi_network_id, db, defer_wifi_validation=defer_wifi_validation)
    network_id = _validate_network(db, type, network_id, device.site_id)

    iface = Interface(
        device_id=device_id,
        name=name,
        type=type,
        mac=mac,
        band=band,
        is_active=is_active,
        connected_wifi_network_id=connected_wifi_network_id,
        network_id=network_id,
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
    band: str | None = None,
    is_active: bool = True,
    connected_wifi_network_id: int | None = None,
    network_id: int | None = None,
    defer_wifi_validation: bool = False,
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

    band = _validate_band(type, band)
    _validate_wifi_links(type, band, connected_wifi_network_id, db, defer_wifi_validation=defer_wifi_validation)
    device = require_found(db.get(Device, iface.device_id), "Device")
    network_id = _validate_network(db, type, network_id, device.site_id)

    iface.name = name
    iface.type = type
    iface.mac = mac
    iface.band = band
    iface.is_active = is_active
    iface.connected_wifi_network_id = connected_wifi_network_id
    iface.network_id = network_id
    db.flush()
    return iface

def delete(db: Session, interface_id: int) -> None:
    iface = get_by_id(db, interface_id)
    if iface is None:
        return

    if iface.type == IFACE_TYPE_WIFI_AP:
        linked = (
            db.query(WiFiNetwork)
            .filter(WiFiNetwork.interface_id == interface_id)
            .count()
        )
        if linked:
            raise ValidationError(
                "Cannot delete Wi-Fi AP interface with linked Wi-Fi networks",
                field="interface_id",
            )

    from app.models.port import Port
    db.query(Port).filter(Port.interface_id == interface_id).delete(synchronize_session=False)

    db.delete(iface)
    db.flush()

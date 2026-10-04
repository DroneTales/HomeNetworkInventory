# Home Network Inventory
# Site networks (subnets) CRUD.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.validation import require_found, validate_ipv4, validate_mask
from app.models.network import Network


def list_all(db: Session, site_id: int) -> list[Network]:
    return (
        db.query(Network)
        .filter(Network.site_id == site_id)
        .order_by(Network.name)
        .all()
    )

def get_by_id(db: Session, network_id: int, site_id: int | None = None) -> Network | None:
    net = db.get(Network, network_id)
    if net is None:
        return None
    if site_id is not None and net.site_id != site_id:
        return None
    return net

def get_by_name(db: Session, name: str, site_id: int) -> Network | None:
    return (
        db.query(Network)
        .filter(Network.name == name, Network.site_id == site_id)
        .first()
    )

def create(
    db: Session,
    site_id: int,
    name: str,
    network_address: str,
    mask: str,
    vlan: int | None = None,
    description: str | None = None,
) -> Network:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    if get_by_name(db, name, site_id) is not None:
        raise ValidationError(
            f"Network '{name}' already exists in this home",
            field="name",
        )

    network_address = validate_ipv4(network_address, field="network_address")
    mask = validate_mask(mask, field="mask")

    network = Network(
        site_id=site_id,
        name=name,
        network_address=network_address,
        mask=mask,
        vlan=vlan,
        description=description or None,
    )
    db.add(network)
    db.flush()
    return network

def update(
    db: Session,
    network_id: int,
    name: str,
    network_address: str,
    mask: str,
    vlan: int | None = None,
    description: str | None = None,
) -> Network:
    network = require_found(get_by_id(db, network_id), "Network")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    existing = get_by_name(db, name, network.site_id)
    if existing is not None and existing.id != network_id:
        raise ValidationError(
            f"Network '{name}' already exists in this home",
            field="name",
        )

    network_address = validate_ipv4(network_address, field="network_address")
    mask = validate_mask(mask, field="mask")

    network.name = name
    network.network_address = network_address
    network.mask = mask
    network.vlan = vlan
    network.description = description or None
    db.flush()
    return network

def delete(db: Session, network_id: int) -> None:
    network = get_by_id(db, network_id)
    if network is None:
        return

    from app.models.device import Device
    from app.models.ip_address import IPAddress

    devices_in_use = (
        db.query(Device)
        .filter(Device.network_id == network_id)
        .count()
    )
    if devices_in_use > 0:
        raise ValidationError(
            f"Cannot delete: {devices_in_use} device(s) belong to this network",
            field="id",
        )

    ips_in_use = (
        db.query(IPAddress)
        .filter(IPAddress.network_id == network_id)
        .count()
    )
    if ips_in_use > 0:
        raise ValidationError(
            f"Cannot delete: {ips_in_use} IP address(es) belong to this network",
            field="id",
        )

    db.delete(network)
    db.flush()


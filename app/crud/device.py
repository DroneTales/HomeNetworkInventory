# Home Network Inventory
# Devices CRUD with reference and consistency checks.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.validation import require_found, validate_hostname
from app.models.device import Device
from app.models.device_type import DeviceType
from app.models.interface import Interface
from app.models.ip_address import IPAddress
from app.models.location import Location
from app.models.model import Model
from app.models.vendor import Vendor


def list_all(db: Session, site_id: int) -> list[Device]:
    return (
        db.query(Device)
        .filter(Device.site_id == site_id)
        .order_by(Device.hostname)
        .all()
    )

def get_by_id(db: Session, device_id: int, site_id: int | None = None) -> Device | None:
    device = db.get(Device, device_id)
    if device is None:
        return None
    if site_id is not None and device.site_id != site_id:
        return None
    return device


def _check_hostname_unique(
    db: Session,
    hostname: str,
    site_id: int,
    exclude_id: int | None = None,
) -> None:
    query = (
        db.query(Device)
        .filter(Device.hostname == hostname, Device.site_id == site_id)
    )
    if exclude_id is not None:
        query = query.filter(Device.id != exclude_id)
    existing = query.first()
    if existing is not None:
        raise ValidationError(
            f"Hostname '{hostname}' already exists in this home",
            field="hostname",
        )

def _check_references(
    db: Session,
    site_id: int,
    device_type_id: int | None,
    vendor_id: int | None,
    model_id: int | None,
    location_id: int | None,
) -> None:
    if device_type_id is not None:
        require_found(db.get(DeviceType, device_type_id), "Device type", field="device_type_id")
    if vendor_id is not None:
        require_found(db.get(Vendor, vendor_id), "Vendor", field="vendor_id")
    if model_id is not None:
        require_found(db.get(Model, model_id), "Model", field="model_id")

    # All references must be scoped to the same site as the device
    if location_id is not None:
        loc = require_found(db.get(Location, location_id), "Location", field="location_id")
        if loc.site_id != site_id:
            raise ValidationError(
                "Location belongs to a different home",
                field="location_id",
            )


def _validate_consistency(db: Session, device: Device) -> None:
    # Active device types require at least one IP; passive ones must have none
    if device.device_type is None:
        return

    has_ip = (
        db.query(IPAddress)
        .join(Interface, IPAddress.interface_id == Interface.id)
        .filter(Interface.device_id == device.id)
        .count()
        > 0
    )

    if device.device_type.is_active and not has_ip:
        raise ValidationError(
            f"Device type '{device.device_type.name}' is active, "
            "but device has no interfaces with IP address",
            field="interfaces",
        )

    if not device.device_type.is_active and has_ip:
        raise ValidationError(
            f"Device type '{device.device_type.name}' is passive, "
            "but device has interface with IP address",
            field="interfaces",
        )

def create(
    db: Session,
    site_id: int,
    hostname: str,
    human_readable_name: str | None = None,
    remarks: str | None = None,
    device_type_id: int | None = None,
    vendor_id: int | None = None,
    model_id: int | None = None,
    location_id: int | None = None,
    is_active: bool = True,
) -> Device:
    hostname = validate_hostname(hostname, field="hostname")

    _check_references(
        db, site_id, device_type_id, vendor_id, model_id, location_id
    )
    _check_hostname_unique(db, hostname, site_id)

    device = Device(
        site_id=site_id,
        hostname=hostname,
        human_readable_name=human_readable_name or None,
        remarks=remarks or None,
        device_type_id=device_type_id,
        vendor_id=vendor_id,
        model_id=model_id,
        location_id=location_id,
        is_active=is_active,
    )
    db.add(device)
    db.flush()
    return device

def update(
    db: Session,
    device_id: int,
    hostname: str,
    human_readable_name: str | None = None,
    remarks: str | None = None,
    device_type_id: int | None = None,
    vendor_id: int | None = None,
    model_id: int | None = None,
    location_id: int | None = None,
    is_active: bool = True,
) -> Device:
    device = require_found(get_by_id(db, device_id), "Device")

    hostname = validate_hostname(hostname, field="hostname")

    _check_references(
        db,
        device.site_id,
        device_type_id,
        vendor_id,
        model_id,
        location_id,
    )
    _check_hostname_unique(db, hostname, device.site_id, exclude_id=device_id)

    device.hostname = hostname
    device.human_readable_name = human_readable_name or None
    device.remarks = remarks or None
    device.device_type_id = device_type_id
    device.vendor_id = vendor_id
    device.model_id = model_id
    device.location_id = location_id
    device.is_active = is_active
    db.flush()
    return device

def delete(db: Session, device_id: int) -> None:
    device = get_by_id(db, device_id)
    if device is None:
        return
    db.delete(device)
    db.flush()

def validate_full(db: Session, device: Device) -> None:
    _validate_consistency(db, device)

def move_to_location(
    db: Session,
    device_id: int,
    site_id: int,
    location_id: int | None,
) -> Device:
    device = require_found(get_by_id(db, device_id, site_id=site_id), "Device")
    if location_id is not None:
        loc = require_found(db.get(Location, location_id), "Location", field="location_id")
        if loc.site_id != site_id:
            raise ValidationError("Location belongs to another site", field="location_id")
    device.location_id = location_id
    db.flush()
    return device


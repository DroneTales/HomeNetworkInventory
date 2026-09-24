from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.validation import validate_hostname
from app.models.device import Device
from app.models.device_type import DeviceType
from app.models.interface import Interface
from app.models.ip_address import IPAddress
from app.models.location import Location
from app.models.model import Model
from app.models.network import Network
from app.models.vendor import Vendor


def list_all(db: Session, site_id: int) -> list[Device]:
    """Все устройства конкретного дома, отсортированные по hostname."""
    return (
        db.query(Device)
        .filter(Device.site_id == site_id)
        .order_by(Device.hostname)
        .all()
    )


def get_by_id(db: Session, device_id: int, site_id: int | None = None) -> Device | None:
    """Устройство по id. Если site_id передан — проверяет принадлежность дому."""
    device = db.get(Device, device_id)
    if device is None:
        return None
    if site_id is not None and device.site_id != site_id:
        return None
    return device


def get_by_hostname(db: Session, hostname: str, site_id: int) -> Device | None:
    return (
        db.query(Device)
        .filter(Device.hostname == hostname, Device.site_id == site_id)
        .first()
    )


def _check_hostname_unique(
    db: Session,
    hostname: str,
    site_id: int,
    exclude_id: int | None = None,
) -> None:
    """Уникальность hostname в пределах дома."""
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
    network_id: int | None,
) -> None:
    """Проверяет существование справочников и принадлежность дому."""
    if device_type_id is not None and db.get(DeviceType, device_type_id) is None:
        raise ValidationError("Device type not found", field="device_type_id")
    if vendor_id is not None and db.get(Vendor, vendor_id) is None:
        raise ValidationError("Vendor not found", field="vendor_id")
    if model_id is not None and db.get(Model, model_id) is None:
        raise ValidationError("Model not found", field="model_id")

    if location_id is not None:
        loc = db.get(Location, location_id)
        if loc is None:
            raise ValidationError("Location not found", field="location_id")
        if loc.site_id != site_id:
            raise ValidationError(
                "Location belongs to a different home",
                field="location_id",
            )

    if network_id is not None:
        net = db.get(Network, network_id)
        if net is None:
            raise ValidationError("Network not found", field="network_id")
        if net.site_id != site_id:
            raise ValidationError(
                "Network belongs to a different home",
                field="network_id",
            )


def _validate_consistency(db: Session, device: Device) -> None:
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
    network_id: int | None = None,
    is_active: bool = True,
) -> Device:
    hostname = validate_hostname(hostname, field="hostname")

    _check_references(
        db, site_id, device_type_id, vendor_id, model_id, location_id, network_id
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
        network_id=network_id,
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
    network_id: int | None = None,
    is_active: bool = True,
) -> Device:
    device = get_by_id(db, device_id)
    if device is None:
        raise ValidationError("Device not found", field="id")

    hostname = validate_hostname(hostname, field="hostname")

    _check_references(
        db,
        device.site_id,
        device_type_id,
        vendor_id,
        model_id,
        location_id,
        network_id,
    )
    _check_hostname_unique(db, hostname, device.site_id, exclude_id=device_id)

    device.hostname = hostname
    device.human_readable_name = human_readable_name or None
    device.remarks = remarks or None
    device.device_type_id = device_type_id
    device.vendor_id = vendor_id
    device.model_id = model_id
    device.location_id = location_id
    device.network_id = network_id
    device.is_active = is_active
    db.flush()
    return device


def delete(db: Session, device_id: int) -> None:
    device = get_by_id(db, device_id)
    if device is None:
        return  # idempotent
    db.delete(device)
    db.flush()


def validate_full(db: Session, device: Device) -> None:
    _validate_consistency(db, device)


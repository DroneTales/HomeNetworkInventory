from sqlalchemy.orm import Session

from app.core.constants import VALID_SERVICE_PROTOCOLS
from app.core.exceptions import ValidationError
from app.core.validation import require_found, validate_choice
from app.models.device import Device
from app.models.service import Service


def list_by_device(db: Session, device_id: int) -> list[Service]:
    return (
        db.query(Service)
        .filter(Service.device_id == device_id)
        .order_by(Service.name)
        .all()
    )

def get_by_id(db: Session, service_id: int) -> Service | None:
    return db.get(Service, service_id)

def _validate(
    name: str,
    protocol: str | None,
    port: int | None,
) -> tuple[str, str | None, int | None]:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    if protocol is not None and protocol.strip():
        protocol = validate_choice(
            protocol.strip().lower(), VALID_SERVICE_PROTOCOLS, "protocol", "protocol"
        )
    else:
        protocol = None

    if port is not None and (not isinstance(port, int) or port < 1 or port > 65535):
        raise ValidationError(
            "Port must be between 1 and 65535",
            field="port",
        )

    return name, protocol, port

def create(
    db: Session,
    device_id: int,
    name: str,
    protocol: str | None = None,
    port: int | None = None,
    url: str | None = None,
    path: str | None = None,
    description: str | None = None,
) -> Service:
    require_found(db.get(Device, device_id), "Device", field="device_id")

    name, protocol, port = _validate(name, protocol, port)

    service = Service(
        device_id=device_id,
        name=name,
        protocol=protocol,
        port=port,
        url=url or None,
        path=path or None,
        description=description or None,
    )
    db.add(service)
    db.flush()
    return service

def update(
    db: Session,
    service_id: int,
    name: str,
    protocol: str | None = None,
    port: int | None = None,
    url: str | None = None,
    path: str | None = None,
    description: str | None = None,
) -> Service:
    service = require_found(get_by_id(db, service_id), "Service")

    name, protocol, port = _validate(name, protocol, port)

    service.name = name
    service.protocol = protocol
    service.port = port
    service.url = url or None
    service.path = path or None
    service.description = description or None
    db.flush()
    return service

def delete(db: Session, service_id: int) -> None:
    service = require_found(get_by_id(db, service_id), "Service")
    db.delete(service)
    db.flush()

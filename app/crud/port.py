from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.device import Device
from app.models.interface import Interface
from app.models.port import Port

def list_by_device(db: Session, device_id: int) -> list[Port]:
    return (
        db.query(Port)
        .filter(Port.device_id == device_id)
        .order_by(Port.name)
        .all()
    )

def get_by_id(db: Session, port_id: int) -> Port | None:
    return db.get(Port, port_id)

def get_by_device_and_name(db: Session, device_id: int, name: str) -> Port | None:
    return (
        db.query(Port)
        .filter(Port.device_id == device_id, Port.name == name)
        .first()
    )

def _validate(
    db: Session,
    device_id: int,
    interface_id: int,
    name: str,
    exclude_id: int | None = None,
) -> str:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Port name is required", field="name")
    if len(name) > 50:
        raise ValidationError("Port name must be at most 50 characters", field="name")

    iface = db.get(Interface, interface_id)
    if iface is None:
        raise ValidationError("Interface not found", field="interface_id")
    if iface.device_id != device_id:
        raise ValidationError(
            "Interface belongs to a different device",
            field="interface_id",
        )

    existing = get_by_device_and_name(db, device_id, name)
    if existing is not None and existing.id != exclude_id:
        raise ValidationError(
            f"Port '{name}' already exists on this device",
            field="name",
        )

    return name

def create(
    db: Session,
    device_id: int,
    interface_id: int,
    name: str,
    description: str | None = None,
) -> Port:
    if db.get(Device, device_id) is None:
        raise ValidationError("Device not found", field="device_id")

    name = _validate(db, device_id, interface_id, name)

    port = Port(
        device_id=device_id,
        interface_id=interface_id,
        name=name,
        description=description or None,
    )
    db.add(port)
    db.flush()
    return port

def update(
    db: Session,
    port_id: int,
    interface_id: int,
    name: str,
    description: str | None = None,
) -> Port:
    port = get_by_id(db, port_id)
    if port is None:
        raise ValidationError("Port not found", field="id")

    name = _validate(db, port.device_id, interface_id, name, exclude_id=port_id)

    port.interface_id = interface_id
    port.name = name
    port.description = description or None
    db.flush()
    return port

def delete(db: Session, port_id: int) -> None:
    port = get_by_id(db, port_id)
    if port is None:
        return
    db.delete(port)
    db.flush()

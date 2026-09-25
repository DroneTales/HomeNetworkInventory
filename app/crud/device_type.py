from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.device_type import DeviceType

def list_all(db: Session) -> list[DeviceType]:
    return db.query(DeviceType).order_by(DeviceType.name).all()

def get_by_id(db: Session, type_id: int) -> DeviceType | None:
    return db.get(DeviceType, type_id)

def get_by_name(db: Session, name: str) -> DeviceType | None:
    return db.query(DeviceType).filter(DeviceType.name == name).first()

def create(
    db: Session,
    name: str,
    is_active: bool = True,
    description: str | None = None,
) -> DeviceType:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    if get_by_name(db, name) is not None:
        raise ValidationError(f"Device type '{name}' already exists", field="name")

    device_type = DeviceType(
        name=name,
        is_active=is_active,
        description=description,
    )
    db.add(device_type)
    db.flush()
    return device_type

def update(
    db: Session,
    type_id: int,
    name: str,
    is_active: bool,
    description: str | None = None,
) -> DeviceType:
    device_type = get_by_id(db, type_id)
    if device_type is None:
        raise ValidationError("Device type not found", field="id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    existing = get_by_name(db, name)
    if existing is not None and existing.id != type_id:
        raise ValidationError(f"Device type '{name}' already exists", field="name")

    device_type.name = name
    device_type.is_active = is_active
    device_type.description = description
    db.flush()
    return device_type

def delete(db: Session, type_id: int) -> None:
    device_type = get_by_id(db, type_id)
    if device_type is None:
        return

    from app.models.device import Device

    in_use = db.query(Device).filter(Device.device_type_id == type_id).count()
    if in_use > 0:
        raise ValidationError(
            f"Cannot delete: {in_use} device(s) use this type",
            field="id",
        )

    db.delete(device_type)
    db.flush()

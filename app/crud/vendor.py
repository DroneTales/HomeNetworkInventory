from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.vendor import Vendor


def list_all(db: Session) -> list[Vendor]:
    """Возвращает всех вендоров, отсортированных по имени."""
    return db.query(Vendor).order_by(Vendor.name).all()


def get_by_id(db: Session, vendor_id: int) -> Vendor | None:
    return db.get(Vendor, vendor_id)


def get_by_name(db: Session, name: str) -> Vendor | None:
    return db.query(Vendor).filter(Vendor.name == name).first()


def create(db: Session, name: str) -> Vendor:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    if get_by_name(db, name) is not None:
        raise ValidationError(f"Vendor '{name}' already exists", field="name")

    vendor = Vendor(name=name)
    db.add(vendor)
    db.flush()
    return vendor


def update(db: Session, vendor_id: int, name: str) -> Vendor:
    vendor = get_by_id(db, vendor_id)
    if vendor is None:
        raise ValidationError("Vendor not found", field="id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    existing = get_by_name(db, name)
    if existing is not None and existing.id != vendor_id:
        raise ValidationError(f"Vendor '{name}' already exists", field="name")

    vendor.name = name
    db.flush()
    return vendor


def delete(db: Session, vendor_id: int) -> None:
    vendor = get_by_id(db, vendor_id)
    if vendor is None:
        return  # already gone, idempotent

    # Проверяем, не ссылаются ли на вендора модели или устройства
    from app.models.device import Device
    from app.models.model import Model

    models_in_use = db.query(Model).filter(Model.vendor_id == vendor_id).count()
    if models_in_use > 0:
        raise ValidationError(
            f"Cannot delete: {models_in_use} model(s) belong to this vendor",
            field="id",
        )

    devices_in_use = db.query(Device).filter(Device.vendor_id == vendor_id).count()
    if devices_in_use > 0:
        raise ValidationError(
            f"Cannot delete: {devices_in_use} device(s) use this vendor",
            field="id",
        )

    db.delete(vendor)
    db.flush()


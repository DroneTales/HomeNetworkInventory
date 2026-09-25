from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.model import Model
from app.models.vendor import Vendor

def list_all(db: Session) -> list[Model]:
    return (
        db.query(Model)
        .join(Vendor)
        .order_by(Vendor.name, Model.name)
        .all()
    )

def list_by_vendor(db: Session, vendor_id: int) -> list[Model]:
    return (
        db.query(Model)
        .filter(Model.vendor_id == vendor_id)
        .order_by(Model.name)
        .all()
    )

def get_by_id(db: Session, model_id: int) -> Model | None:
    return db.get(Model, model_id)

def get_by_vendor_and_name(db: Session, vendor_id: int, name: str) -> Model | None:
    return (
        db.query(Model)
        .filter(Model.vendor_id == vendor_id, Model.name == name)
        .first()
    )

def create(db: Session, vendor_id: int, name: str) -> Model:
    if not vendor_id:
        raise ValidationError("Vendor is required", field="vendor_id")

    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise ValidationError("Vendor not found", field="vendor_id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    if get_by_vendor_and_name(db, vendor_id, name) is not None:
        raise ValidationError(
            f"Model '{name}' already exists for vendor '{vendor.name}'",
            field="name",
        )

    model = Model(vendor_id=vendor_id, name=name)
    db.add(model)
    db.flush()
    return model

def update(db: Session, model_id: int, vendor_id: int, name: str) -> Model:
    model = get_by_id(db, model_id)
    if model is None:
        raise ValidationError("Model not found", field="id")

    if not vendor_id:
        raise ValidationError("Vendor is required", field="vendor_id")

    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise ValidationError("Vendor not found", field="vendor_id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    existing = get_by_vendor_and_name(db, vendor_id, name)
    if existing is not None and existing.id != model_id:
        raise ValidationError(
            f"Model '{name}' already exists for vendor '{vendor.name}'",
            field="name",
        )

    model.vendor_id = vendor_id
    model.name = name
    db.flush()
    return model

def delete(db: Session, model_id: int) -> None:
    model = get_by_id(db, model_id)
    if model is None:
        return

    from app.models.device import Device

    in_use = db.query(Device).filter(Device.model_id == model_id).count()
    if in_use > 0:
        raise ValidationError(
            f"Cannot delete: {in_use} device(s) use this model",
            field="id",
        )

    db.delete(model)
    db.flush()

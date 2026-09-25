from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.location import Location

def list_all(db: Session, site_id: int) -> list[Location]:
    return (
        db.query(Location)
        .filter(Location.site_id == site_id)
        .order_by(Location.name)
        .all()
    )

def get_by_id(db: Session, location_id: int, site_id: int | None = None) -> Location | None:
    loc = db.get(Location, location_id)
    if loc is None:
        return None
    if site_id is not None and loc.site_id != site_id:
        return None
    return loc

def get_by_name(db: Session, name: str, site_id: int) -> Location | None:
    return (
        db.query(Location)
        .filter(Location.name == name, Location.site_id == site_id)
        .first()
    )

def create(
    db: Session,
    site_id: int,
    name: str,
    description: str | None = None,
) -> Location:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    if get_by_name(db, name, site_id) is not None:
        raise ValidationError(
            f"Location '{name}' already exists in this home",
            field="name",
        )

    location = Location(
        site_id=site_id,
        name=name,
        description=description or None,
    )
    db.add(location)
    db.flush()
    return location

def update(
    db: Session,
    location_id: int,
    name: str,
    description: str | None = None,
) -> Location:
    location = get_by_id(db, location_id)
    if location is None:
        raise ValidationError("Location not found", field="id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    existing = get_by_name(db, name, location.site_id)
    if existing is not None and existing.id != location_id:
        raise ValidationError(
            f"Location '{name}' already exists in this home",
            field="name",
        )

    location.name = name
    location.description = description or None
    db.flush()
    return location

def delete(db: Session, location_id: int) -> None:
    location = get_by_id(db, location_id)
    if location is None:
        return

    from app.models.device import Device

    in_use = (
        db.query(Device)
        .filter(Device.location_id == location_id)
        .count()
    )
    if in_use > 0:
        raise ValidationError(
            f"Cannot delete: {in_use} device(s) use this location",
            field="id",
        )

    db.delete(location)
    db.flush()

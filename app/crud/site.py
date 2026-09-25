from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.device import Device
from app.models.location import Location
from app.models.network import Network
from app.models.site import Site
from app.models.user import User
from app.models.user_site import UserSite

def list_all(db: Session, include_inactive: bool = False) -> list[Site]:
    query = db.query(Site)
    if not include_inactive:
        query = query.filter(Site.is_active == True)  # noqa: E712
    return query.order_by(Site.name).all()

def get_by_id(db: Session, site_id: int) -> Site | None:
    return db.get(Site, site_id)

def get_by_name(db: Session, name: str) -> Site | None:
    return db.query(Site).filter(Site.name == name).first()

def create(
    db: Session,
    name: str,
    address: str | None = None,
    photo: bytes | None = None,
    photo_mime: str | None = None,
    is_active: bool = True,
) -> Site:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")
    if len(name) > 100:
        raise ValidationError("Name must be at most 100 characters", field="name")

    if get_by_name(db, name) is not None:
        raise ValidationError(f"Home '{name}' already exists", field="name")

    site = Site(
        name=name,
        address=(address or "").strip() or None,
        photo=photo,
        photo_mime=photo_mime,
        is_active=is_active,
    )
    db.add(site)
    db.flush()
    return site

def update(
    db: Session,
    site_id: int,
    name: str,
    address: str | None = None,
    photo: bytes | None = None,
    photo_mime: str | None = None,
    is_active: bool = True,
) -> Site:
    site = get_by_id(db, site_id)
    if site is None:
        raise ValidationError("Home not found", field="id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")
    if len(name) > 100:
        raise ValidationError("Name must be at most 100 characters", field="name")

    existing = get_by_name(db, name)
    if existing is not None and existing.id != site_id:
        raise ValidationError(f"Home '{name}' already exists", field="name")

    site.name = name
    site.address = (address or "").strip() or None
    site.is_active = is_active
    if photo is not None:
        site.photo = photo
        site.photo_mime = photo_mime
    db.flush()
    return site

def clear_photo(db: Session, site_id: int) -> Site:
    site = get_by_id(db, site_id)
    if site is None:
        raise ValidationError("Home not found", field="id")
    site.photo = None
    site.photo_mime = None
    db.flush()
    return site

def is_empty(db: Session, site_id: int) -> bool:
    for model in (Device, Location, Network):
        count = db.query(model).filter(model.site_id == site_id).count()
        if count > 0:
            return False
    return True

def delete(db: Session, site_id: int) -> None:
    site = get_by_id(db, site_id)
    if site is None:
        return

    if not is_empty(db, site_id):
        raise ValidationError(
            "Cannot delete: home is not empty. "
            "Remove or move devices, locations, and networks first.",
            field="id",
        )

    db.delete(site)
    db.flush()

def list_users(db: Session, site_id: int) -> list[User]:
    return (
        db.query(User)
        .join(UserSite, UserSite.user_id == User.id)
        .filter(UserSite.site_id == site_id)
        .order_by(User.username)
        .all()
    )

def is_user_assigned(db: Session, user_id: int, site_id: int) -> bool:
    return (
        db.query(UserSite)
        .filter(UserSite.user_id == user_id, UserSite.site_id == site_id)
        .first()
        is not None
    )

def assign_user(db: Session, user_id: int, site_id: int) -> None:
    if db.get(User, user_id) is None:
        raise ValidationError("User not found", field="user_id")
    if db.get(Site, site_id) is None:
        raise ValidationError("Home not found", field="site_id")

    if is_user_assigned(db, user_id, site_id):
        return

    db.add(UserSite(user_id=user_id, site_id=site_id))
    db.flush()

def unassign_user(db: Session, user_id: int, site_id: int) -> None:
    link = (
        db.query(UserSite)
        .filter(UserSite.user_id == user_id, UserSite.site_id == site_id)
        .first()
    )
    if link is None:
        return
    db.delete(link)
    db.flush()

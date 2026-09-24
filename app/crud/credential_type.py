from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.credential_type import CredentialType


def list_all(db: Session) -> list[CredentialType]:
    return db.query(CredentialType).order_by(CredentialType.name).all()


def get_by_id(db: Session, type_id: int) -> CredentialType | None:
    return db.get(CredentialType, type_id)


def get_by_name(db: Session, name: str) -> CredentialType | None:
    return db.query(CredentialType).filter(CredentialType.name == name).first()


def create(
    db: Session,
    name: str,
    description: str | None = None,
) -> CredentialType:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    if get_by_name(db, name) is not None:
        raise ValidationError(f"Credential type '{name}' already exists", field="name")

    ct = CredentialType(name=name, description=description or None)
    db.add(ct)
    db.flush()
    return ct


def update(
    db: Session,
    type_id: int,
    name: str,
    description: str | None = None,
) -> CredentialType:
    ct = get_by_id(db, type_id)
    if ct is None:
        raise ValidationError("Credential type not found", field="id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    existing = get_by_name(db, name)
    if existing is not None and existing.id != type_id:
        raise ValidationError(f"Credential type '{name}' already exists", field="name")

    ct.name = name
    ct.description = description or None
    db.flush()
    return ct


def delete(db: Session, type_id: int) -> None:
    """Удаляет тип. У связанных credentials поле type_id станет NULL
    благодаря ondelete='SET NULL' на FK."""
    ct = get_by_id(db, type_id)
    if ct is None:
        return  # already gone, idempotent
    db.delete(ct)
    db.flush()


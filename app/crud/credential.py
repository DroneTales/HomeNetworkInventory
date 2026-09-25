from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.credential import Credential
from app.models.credential_type import CredentialType
from app.models.device import Device

def list_by_device(db: Session, device_id: int) -> list[Credential]:
    return (
        db.query(Credential)
        .filter(Credential.device_id == device_id)
        .order_by(Credential.username)
        .all()
    )

def get_by_id(db: Session, credential_id: int) -> Credential | None:
    return db.get(Credential, credential_id)

def _validate(
    type_id: int | None,
    username: str | None,
    password: str | None,
) -> tuple[int | None, str | None, str | None]:
    username = (username or "").strip() or None
    password = password if password is not None and password != "" else None

    if username is None and password is None:
        raise ValidationError(
            "Either username or password must be provided",
            field="username",
        )

    return type_id, username, password

def create(
    db: Session,
    device_id: int,
    type_id: int | None = None,
    username: str | None = None,
    password: str | None = None,
    description: str | None = None,
) -> Credential:
    if db.get(Device, device_id) is None:
        raise ValidationError("Device not found", field="device_id")

    if type_id is not None and db.get(CredentialType, type_id) is None:
        raise ValidationError("Credential type not found", field="type_id")

    type_id, username, password = _validate(type_id, username, password)

    cred = Credential(
        device_id=device_id,
        type_id=type_id,
        username=username,
        password=password,
        description=description or None,
    )
    db.add(cred)
    db.flush()
    return cred

def update(
    db: Session,
    credential_id: int,
    type_id: int | None = None,
    username: str | None = None,
    password: str | None = None,
    description: str | None = None,
) -> Credential:
    cred = get_by_id(db, credential_id)
    if cred is None:
        raise ValidationError("Credential not found", field="id")

    if type_id is not None and db.get(CredentialType, type_id) is None:
        raise ValidationError("Credential type not found", field="type_id")

    type_id, username, password = _validate(type_id, username, password)

    cred.type_id = type_id
    cred.username = username
    cred.password = password
    cred.description = description or None
    db.flush()
    return cred

def delete(db: Session, credential_id: int) -> None:
    cred = get_by_id(db, credential_id)
    if cred is None:
        raise ValidationError("Credential not found", field="id")
    db.delete(cred)
    db.flush()

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.connection import Connection
from app.models.device import Device
from app.models.port import Port

VALID_TYPES = {"physical", "logical"}


def list_all(db: Session, site_id: int) -> list[Connection]:
    """Все связи внутри дома.

    Связь принадлежит дому, если её source-порт и target-порт — из
    устройств этого дома.
    """
    return (
        db.query(Connection)
        .join(Port, Connection.source_port_id == Port.id)
        .join(Device, Port.device_id == Device.id)
        .filter(Device.site_id == site_id)
        .order_by(Connection.id)
        .all()
    )


def list_by_port(db: Session, port_id: int) -> list[Connection]:
    return (
        db.query(Connection)
        .filter(
            or_(
                Connection.source_port_id == port_id,
                Connection.target_port_id == port_id,
            )
        )
        .order_by(Connection.id)
        .all()
    )


def list_by_device(db: Session, device_id: int) -> list[Connection]:
    port_ids = [
        row[0]
        for row in db.query(Port.id).filter(Port.device_id == device_id).all()
    ]
    if not port_ids:
        return []
    return (
        db.query(Connection)
        .filter(
            or_(
                Connection.source_port_id.in_(port_ids),
                Connection.target_port_id.in_(port_ids),
            )
        )
        .order_by(Connection.id)
        .all()
    )


def get_by_id(
    db: Session,
    connection_id: int,
    site_id: int | None = None,
) -> Connection | None:
    """Связь по id. Если site_id передан — проверяет, что оба порта из этого дома."""
    conn = db.get(Connection, connection_id)
    if conn is None:
        return None
    if site_id is None:
        return conn

    source_dev = db.query(Device).join(Port, Port.device_id == Device.id).filter(
        Port.id == conn.source_port_id
    ).first()
    target_dev = db.query(Device).join(Port, Port.device_id == Device.id).filter(
        Port.id == conn.target_port_id
    ).first()

    if source_dev is None or target_dev is None:
        return None
    if source_dev.site_id != site_id or target_dev.site_id != site_id:
        return None
    return conn


def _check_port(db: Session, port_id: int, site_id: int, field: str) -> Port:
    """Проверяет, что порт существует и принадлежит устройству этого дома."""
    port = db.get(Port, port_id)
    if port is None:
        raise ValidationError("Port not found", field=field)

    device = db.get(Device, port.device_id)
    if device is None or device.site_id != site_id:
        raise ValidationError(
            "Port belongs to a different home",
            field=field,
        )
    return port


def _check_not_same(source_port_id: int, target_port_id: int) -> None:
    if source_port_id == target_port_id:
        raise ValidationError(
            "Source and target ports cannot be the same",
            field="target_port_id",
        )


def _check_duplicate(
    db: Session,
    source_port_id: int,
    target_port_id: int,
    exclude_id: int | None = None,
) -> None:
    """A→B и B→A — одна и та же физическая связь, поэтому обе считаются дубликатом."""
    query = db.query(Connection).filter(
        or_(
            (Connection.source_port_id == source_port_id)
            & (Connection.target_port_id == target_port_id),
            (Connection.source_port_id == target_port_id)
            & (Connection.target_port_id == source_port_id),
        )
    )
    if exclude_id is not None:
        query = query.filter(Connection.id != exclude_id)

    if query.first() is not None:
        raise ValidationError(
            "This connection already exists",
            field="source_port_id",
        )


def _validate(
    db: Session,
    site_id: int,
    source_port_id: int,
    target_port_id: int,
    connection_type: str,
    exclude_id: int | None = None,
) -> str:
    connection_type = (connection_type or "").strip().lower()
    if connection_type not in VALID_TYPES:
        raise ValidationError(
            f"Invalid connection type: {connection_type}. "
            f"Allowed: {', '.join(sorted(VALID_TYPES))}",
            field="connection_type",
        )

    _check_port(db, source_port_id, site_id, field="source_port_id")
    _check_port(db, target_port_id, site_id, field="target_port_id")
    _check_not_same(source_port_id, target_port_id)
    _check_duplicate(db, source_port_id, target_port_id, exclude_id=exclude_id)

    return connection_type


def create(
    db: Session,
    site_id: int,
    source_port_id: int,
    target_port_id: int,
    connection_type: str = "physical",
    cable_type: str | None = None,
    description: str | None = None,
    is_active: bool = True,
) -> Connection:
    connection_type = _validate(
        db, site_id, source_port_id, target_port_id, connection_type
    )

    conn = Connection(
        source_port_id=source_port_id,
        target_port_id=target_port_id,
        connection_type=connection_type,
        cable_type=cable_type or None,
        description=description or None,
        is_active=is_active,
    )
    db.add(conn)
    db.flush()
    return conn


def update(
    db: Session,
    connection_id: int,
    site_id: int,
    source_port_id: int,
    target_port_id: int,
    connection_type: str = "physical",
    cable_type: str | None = None,
    description: str | None = None,
    is_active: bool = True,
) -> Connection:
    conn = get_by_id(db, connection_id, site_id=site_id)
    if conn is None:
        raise ValidationError("Connection not found", field="id")

    connection_type = _validate(
        db, site_id, source_port_id, target_port_id, connection_type,
        exclude_id=connection_id,
    )

    conn.source_port_id = source_port_id
    conn.target_port_id = target_port_id
    conn.connection_type = connection_type
    conn.cable_type = cable_type or None
    conn.description = description or None
    conn.is_active = is_active
    db.flush()
    return conn


def delete(db: Session, connection_id: int) -> None:
    conn = db.get(Connection, connection_id)
    if conn is None:
        return  # idempotent
    db.delete(conn)
    db.flush()


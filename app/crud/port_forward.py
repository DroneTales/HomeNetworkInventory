from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.constants import PF_PROTOCOL_BOTH, VALID_PF_PROTOCOLS
from app.core.exceptions import ValidationError
from app.core.validation import require_found, validate_choice, validate_ipv4
from app.models.device import Device
from app.models.port_forward import PortForward


def list_by_device(db: Session, device_id: int) -> list[PortForward]:
    return (
        db.query(PortForward)
        .filter(PortForward.device_id == device_id)
        .order_by(PortForward.external_port_start, PortForward.protocol)
        .all()
    )


def get_by_id(db: Session, pf_id: int) -> PortForward | None:
    return db.get(PortForward, pf_id)


def list_incoming(
    db: Session,
    device_id: int,
    site_id: int,
    ip_addresses: list[str],
) -> list[PortForward]:
    conds = [PortForward.internal_device_id == device_id]
    if ip_addresses:
        conds.append(PortForward.internal_ip_manual.in_(ip_addresses))
    return (
        db.query(PortForward)
        .join(Device, PortForward.device_id == Device.id)
        .filter(
            Device.site_id == site_id,
            or_(*conds),
        )
        .order_by(PortForward.external_port_start, PortForward.protocol)
        .all()
    )


def _validate_ports(
    start,
    end,
    field_start: str,
    field_end: str,
) -> tuple[int, int]:
    try:
        start = int(start)
        end = int(end)
    except (TypeError, ValueError):
        raise ValidationError("Port must be an integer", field=field_start) from None

    if start < 1 or start > 65535:
        raise ValidationError("Port must be between 1 and 65535", field=field_start)
    if end < 1 or end > 65535:
        raise ValidationError("Port must be between 1 and 65535", field=field_end)
    if start > end:
        raise ValidationError(
            f"Start port {start} must be less than or equal to end port {end}",
            field=field_start,
        )
    return start, end


def _protocols_overlap(a: str, b: str) -> bool:
    if a == PF_PROTOCOL_BOTH or b == PF_PROTOCOL_BOTH:
        return True
    return a == b


def _ranges_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    return s1 <= e2 and s2 <= e1


def _check_overlap(
    db: Session,
    device_id: int,
    external_port_start: int,
    external_port_end: int,
    protocol: str,
    exclude_id: int | None = None,
) -> None:
    query = db.query(PortForward).filter(
        PortForward.device_id == device_id,
        PortForward.is_active.is_(True),
    )
    if exclude_id is not None:
        query = query.filter(PortForward.id != exclude_id)

    for other in query.all():
        if not _protocols_overlap(protocol, other.protocol):
            continue
        if _ranges_overlap(
            external_port_start,
            external_port_end,
            other.external_port_start,
            other.external_port_end,
        ):
            raise ValidationError(
                f"External port range {external_port_start}-{external_port_end} "
                f"({protocol}) overlaps with existing rule "
                f"{other.external_port_start}-{other.external_port_end} "
                f"({other.protocol})",
                field="external_port_start",
            )


def _validate(
    db: Session,
    device_id: int,
    external_port_start,
    external_port_end,
    protocol: str,
    internal_device_id: int | None,
    internal_ip_manual: str | None,
    internal_port_start,
    internal_port_end,
    exclude_id: int | None = None,
) -> tuple:
    device = require_found(db.get(Device, device_id), "Device", field="device_id")

    external_port_start, external_port_end = _validate_ports(
        external_port_start,
        external_port_end,
        "external_port_start",
        "external_port_end",
    )
    internal_port_start, internal_port_end = _validate_ports(
        internal_port_start,
        internal_port_end,
        "internal_port_start",
        "internal_port_end",
    )

    protocol = validate_choice(
        (protocol or "").strip().lower(), VALID_PF_PROTOCOLS, "protocol", "protocol"
    )

    has_device_target = internal_device_id is not None
    manual = (internal_ip_manual or "").strip()
    has_manual_target = bool(manual)

    if has_device_target and has_manual_target:
        raise ValidationError(
            "Specify either internal device or manual IP, not both",
            field="internal_device_id",
        )
    if not has_device_target and not has_manual_target:
        raise ValidationError(
            "Internal device or manual IP is required",
            field="internal_device_id",
        )

    if has_device_target:
        internal = db.get(Device, internal_device_id)
        if internal is None:
            raise ValidationError(
                "Internal device not found", field="internal_device_id"
            )
        if internal.site_id != device.site_id:
            raise ValidationError(
                "Internal device belongs to a different home",
                field="internal_device_id",
            )
        internal_ip_manual = None
    else:
        internal_ip_manual = validate_ipv4(manual, field="internal_ip_manual")
        internal_device_id = None

    _check_overlap(
        db,
        device_id,
        external_port_start,
        external_port_end,
        protocol,
        exclude_id=exclude_id,
    )

    return (
        external_port_start,
        external_port_end,
        protocol,
        internal_device_id,
        internal_ip_manual,
        internal_port_start,
        internal_port_end,
    )


def create(
    db: Session,
    device_id: int,
    external_port_start,
    external_port_end,
    protocol: str,
    internal_port_start,
    internal_port_end,
    internal_device_id: int | None = None,
    internal_ip_manual: str | None = None,
    description: str | None = None,
    is_active: bool = True,
) -> PortForward:
    (
        external_port_start,
        external_port_end,
        protocol,
        internal_device_id,
        internal_ip_manual,
        internal_port_start,
        internal_port_end,
    ) = _validate(
        db,
        device_id,
        external_port_start,
        external_port_end,
        protocol,
        internal_device_id,
        internal_ip_manual,
        internal_port_start,
        internal_port_end,
    )

    pf = PortForward(
        device_id=device_id,
        external_port_start=external_port_start,
        external_port_end=external_port_end,
        protocol=protocol,
        internal_device_id=internal_device_id,
        internal_ip_manual=internal_ip_manual,
        internal_port_start=internal_port_start,
        internal_port_end=internal_port_end,
        description=description or None,
        is_active=is_active,
    )
    db.add(pf)
    db.flush()
    return pf


def update(
    db: Session,
    pf_id: int,
    external_port_start,
    external_port_end,
    protocol: str,
    internal_port_start,
    internal_port_end,
    internal_device_id: int | None = None,
    internal_ip_manual: str | None = None,
    description: str | None = None,
    is_active: bool = True,
) -> PortForward:
    pf = require_found(get_by_id(db, pf_id), "Port forward rule")

    (
        external_port_start,
        external_port_end,
        protocol,
        internal_device_id,
        internal_ip_manual,
        internal_port_start,
        internal_port_end,
    ) = _validate(
        db,
        pf.device_id,
        external_port_start,
        external_port_end,
        protocol,
        internal_device_id,
        internal_ip_manual,
        internal_port_start,
        internal_port_end,
        exclude_id=pf_id,
    )

    pf.external_port_start = external_port_start
    pf.external_port_end = external_port_end
    pf.protocol = protocol
    pf.internal_device_id = internal_device_id
    pf.internal_ip_manual = internal_ip_manual
    pf.internal_port_start = internal_port_start
    pf.internal_port_end = internal_port_end
    pf.description = description or None
    pf.is_active = is_active
    db.flush()
    return pf


def delete(db: Session, pf_id: int) -> None:
    pf = get_by_id(db, pf_id)
    if pf is None:
        return
    db.delete(pf)
    db.flush()

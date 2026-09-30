from sqlalchemy.orm import Session

from app.core.constants import DHCP_POOL_TYPE_DYNAMIC, VALID_DHCP_POOL_TYPES
from app.core.exceptions import ValidationError
from app.core.validation import require_found, validate_choice, validate_ipv4
from app.models.device import Device
from app.models.dhcp_pool import DhcpPool


def list_by_device(db: Session, device_id: int) -> list[DhcpPool]:
    return (
        db.query(DhcpPool)
        .filter(DhcpPool.device_id == device_id)
        .order_by(DhcpPool.start_ip)
        .all()
    )

def list_all(db: Session) -> list[DhcpPool]:
    return db.query(DhcpPool).order_by(DhcpPool.start_ip).all()

def get_by_id(db: Session, pool_id: int) -> DhcpPool | None:
    return db.get(DhcpPool, pool_id)

def create(
    db: Session,
    device_id: int,
    start_ip: str,
    end_ip: str,
    type: str = DHCP_POOL_TYPE_DYNAMIC,
    name: str | None = None,
    gateway: str | None = None,
    dns: str | None = None,
    description: str | None = None,
) -> DhcpPool:
    require_found(db.get(Device, device_id), "Device", field="device_id")

    type = validate_choice(
        (type or "").strip().lower(), VALID_DHCP_POOL_TYPES, "pool type", "type"
    )

    start_ip = validate_ipv4(start_ip, field="start_ip")
    end_ip = validate_ipv4(end_ip, field="end_ip")

    from ipaddress import IPv4Address

    if IPv4Address(start_ip) > IPv4Address(end_ip):
        raise ValidationError(
            f"Start IP {start_ip} must be less than or equal to end IP {end_ip}",
            field="start_ip",
        )

    if gateway is not None and gateway.strip():
        gateway = validate_ipv4(gateway, field="gateway")
    else:
        gateway = None

    dns = validate_ipv4(dns, field="dns") if dns is not None and dns.strip() else None

    pool = DhcpPool(
        device_id=device_id,
        name=name or None,
        start_ip=start_ip,
        end_ip=end_ip,
        type=type,
        gateway=gateway,
        dns=dns,
        description=description or None,
    )
    db.add(pool)
    db.flush()
    return pool

def update(
    db: Session,
    pool_id: int,
    start_ip: str,
    end_ip: str,
    type: str,
    name: str | None = None,
    gateway: str | None = None,
    dns: str | None = None,
    description: str | None = None,
) -> DhcpPool:
    pool = require_found(get_by_id(db, pool_id), "DHCP pool")

    type = validate_choice(
        (type or "").strip().lower(), VALID_DHCP_POOL_TYPES, "pool type", "type"
    )

    start_ip = validate_ipv4(start_ip, field="start_ip")
    end_ip = validate_ipv4(end_ip, field="end_ip")

    from ipaddress import IPv4Address

    if IPv4Address(start_ip) > IPv4Address(end_ip):
        raise ValidationError(
            f"Start IP {start_ip} must be less than or equal to end IP {end_ip}",
            field="start_ip",
        )

    if gateway is not None and gateway.strip():
        gateway = validate_ipv4(gateway, field="gateway")
    else:
        gateway = None

    dns = validate_ipv4(dns, field="dns") if dns is not None and dns.strip() else None

    pool.name = name or None
    pool.start_ip = start_ip
    pool.end_ip = end_ip
    pool.type = type
    pool.gateway = gateway
    pool.dns = dns
    pool.description = description or None
    db.flush()
    return pool

def delete(db: Session, pool_id: int) -> None:
    pool = require_found(get_by_id(db, pool_id), "DHCP pool")
    db.delete(pool)
    db.flush()

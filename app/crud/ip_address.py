from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.validation import (
    is_ip_in_range,
    validate_ipv4,
    validate_mask,
    validate_same_subnet,
)
from app.models.device import Device
from app.models.dhcp_pool import DhcpPool
from app.models.interface import Interface
from app.models.ip_address import IPAddress

VALID_ADDRESS_TYPES = {"static", "dhcp", "external", "reserved"}
MAC_REQUIRED_TYPES = {"dhcp", "reserved"}
EXTERNAL_DEFAULT_MASK = "255.255.255.255"


def list_by_interface(db: Session, interface_id: int) -> list[IPAddress]:
    return (
        db.query(IPAddress)
        .filter(IPAddress.interface_id == interface_id)
        .order_by(IPAddress.address)
        .all()
    )


def get_by_id(db: Session, ip_id: int) -> IPAddress | None:
    return db.get(IPAddress, ip_id)


def _check_ip_unique(
    db: Session,
    address: str,
    site_id: int,
    exclude_id: int | None = None,
) -> None:
    query = (
        db.query(IPAddress)
        .join(Interface, IPAddress.interface_id == Interface.id)
        .join(Device, Interface.device_id == Device.id)
        .filter(IPAddress.address == address, Device.site_id == site_id)
    )
    if exclude_id is not None:
        query = query.filter(IPAddress.id != exclude_id)

    if query.first() is not None:
        raise ValidationError(
            f"IP address '{address}' already exists in this home",
            field="address",
        )


def _check_interface_type(
    db: Session,
    interface_id: int,
    address_type: str,
) -> Interface:
    iface = db.get(Interface, interface_id)
    if iface is None:
        raise ValidationError("Interface not found", field="interface_id")

    if iface.type == "port":
        raise ValidationError(
            "Interface of type 'port' cannot have an IP address",
            field="interface_id",
        )

    if address_type in MAC_REQUIRED_TYPES and not iface.mac:
        raise ValidationError(
            f"MAC address is required on the interface for address type '{address_type}'",
            field="mac",
        )

    return iface


def validate(
    db: Session,
    interface_id: int,
    address: str | None,
    mask: str | None,
    address_type: str,
    gateway: str | None = None,
    dns: str | None = None,
    exclude_id: int | None = None,
) -> tuple[str | None, str | None, str | None, str | None]:
    address_type = (address_type or "").strip().lower()
    if address_type not in VALID_ADDRESS_TYPES:
        raise ValidationError(
            f"Invalid address type: {address_type}. "
            f"Allowed: {', '.join(sorted(VALID_ADDRESS_TYPES))}",
            field="address_type",
        )

    address = (address or "").strip()
    mask = (mask or "").strip()

    if address_type == "dhcp":
        address = validate_ipv4(address, field="address") if address else None
        mask = validate_mask(mask, field="mask") if mask else None
    else:
        address = validate_ipv4(address, field="address")
        if address_type == "external":
            mask = validate_mask(mask, field="mask") if mask else EXTERNAL_DEFAULT_MASK
        else:
            mask = validate_mask(mask, field="mask")

    if gateway is not None and gateway.strip():
        gateway = validate_ipv4(gateway, field="gateway")
        if address is not None and mask is not None and address_type != "external":
            validate_same_subnet(address, mask, gateway, field="gateway")
    else:
        gateway = None

    if dns is not None and dns.strip():
        dns = validate_ipv4(dns, field="dns")
    else:
        dns = None

    iface = _check_interface_type(db, interface_id, address_type)
    device = db.get(Device, iface.device_id)
    if device is None:
        raise ValidationError("Device not found", field="interface_id")

    if address is not None:
        _check_ip_unique(db, address, site_id=device.site_id, exclude_id=exclude_id)

    return address, mask, gateway, dns


def create(
    db: Session,
    interface_id: int,
    address: str | None,
    mask: str | None,
    address_type: str,
    gateway: str | None = None,
    dns: str | None = None,
    network_id: int | None = None,
    is_primary: bool = True,
) -> IPAddress:
    address, mask, gateway, dns = validate(
        db, interface_id, address, mask, address_type,
        gateway=gateway, dns=dns,
    )

    ip = IPAddress(
        interface_id=interface_id,
        network_id=network_id,
        address=address,
        mask=mask,
        gateway=gateway,
        dns=dns,
        address_type=address_type.strip().lower(),
        is_primary=is_primary,
    )
    db.add(ip)
    db.flush()
    return ip


def update(
    db: Session,
    ip_id: int,
    interface_id: int,
    address: str | None,
    mask: str | None,
    address_type: str,
    gateway: str | None = None,
    dns: str | None = None,
    network_id: int | None = None,
    is_primary: bool = True,
) -> IPAddress:
    ip = get_by_id(db, ip_id)
    if ip is None:
        raise ValidationError("IP address not found", field="id")

    address, mask, gateway, dns = validate(
        db, interface_id, address, mask, address_type,
        gateway=gateway, dns=dns, exclude_id=ip_id,
    )

    ip.interface_id = interface_id
    ip.network_id = network_id
    ip.address = address
    ip.mask = mask
    ip.gateway = gateway
    ip.dns = dns
    ip.address_type = address_type.strip().lower()
    ip.is_primary = is_primary
    db.flush()
    return ip


def delete(db: Session, ip_id: int) -> None:
    ip = get_by_id(db, ip_id)
    if ip is None:
        return
    db.delete(ip)
    db.flush()


def check_ip_in_dhcp_pools(
    db: Session,
    address: str | None,
    site_id: int | None = None,
) -> list[DhcpPool]:
    if not address:
        return []

    query = db.query(DhcpPool)
    if site_id is not None:
        query = (
            query.join(Device, DhcpPool.device_id == Device.id)
            .filter(Device.site_id == site_id)
        )
    pools = query.all()

    result = []
    for pool in pools:
        if is_ip_in_range(address, pool.start_ip, pool.end_ip):
            result.append(pool)
    return result

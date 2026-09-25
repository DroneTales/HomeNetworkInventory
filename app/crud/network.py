import ipaddress

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.validation import validate_ipv4, validate_mask, validate_same_subnet
from app.models.network import Network

def list_all(db: Session, site_id: int) -> list[Network]:
    return (
        db.query(Network)
        .filter(Network.site_id == site_id)
        .order_by(Network.name)
        .all()
    )

def get_by_id(db: Session, network_id: int, site_id: int | None = None) -> Network | None:
    net = db.get(Network, network_id)
    if net is None:
        return None
    if site_id is not None and net.site_id != site_id:
        return None
    return net

def get_by_name(db: Session, name: str, site_id: int) -> Network | None:
    return (
        db.query(Network)
        .filter(Network.name == name, Network.site_id == site_id)
        .first()
    )

def create(
    db: Session,
    site_id: int,
    name: str,
    network_address: str,
    mask: str,
    gateway: str | None = None,
    vlan: int | None = None,
    description: str | None = None,
) -> Network:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    if get_by_name(db, name, site_id) is not None:
        raise ValidationError(
            f"Network '{name}' already exists in this home",
            field="name",
        )

    network_address = validate_ipv4(network_address, field="network_address")
    mask = validate_mask(mask, field="mask")

    if gateway is not None and gateway.strip():
        gateway = validate_ipv4(gateway, field="gateway")
        validate_same_subnet(network_address, mask, gateway, field="gateway")
    else:
        gateway = None

    network = Network(
        site_id=site_id,
        name=name,
        network_address=network_address,
        mask=mask,
        gateway=gateway,
        vlan=vlan,
        description=description or None,
    )
    db.add(network)
    db.flush()
    return network

def update(
    db: Session,
    network_id: int,
    name: str,
    network_address: str,
    mask: str,
    gateway: str | None = None,
    vlan: int | None = None,
    description: str | None = None,
) -> Network:
    network = get_by_id(db, network_id)
    if network is None:
        raise ValidationError("Network not found", field="id")

    name = (name or "").strip()
    if not name:
        raise ValidationError("Name is required", field="name")

    existing = get_by_name(db, name, network.site_id)
    if existing is not None and existing.id != network_id:
        raise ValidationError(
            f"Network '{name}' already exists in this home",
            field="name",
        )

    network_address = validate_ipv4(network_address, field="network_address")
    mask = validate_mask(mask, field="mask")

    if gateway is not None and gateway.strip():
        gateway = validate_ipv4(gateway, field="gateway")
        validate_same_subnet(network_address, mask, gateway, field="gateway")
    else:
        gateway = None

    network.name = name
    network.network_address = network_address
    network.mask = mask
    network.gateway = gateway
    network.vlan = vlan
    network.description = description or None
    db.flush()
    return network

def delete(db: Session, network_id: int) -> None:
    network = get_by_id(db, network_id)
    if network is None:
        return

    from app.models.device import Device
    from app.models.ip_address import IPAddress

    devices_in_use = (
        db.query(Device)
        .filter(Device.network_id == network_id)
        .count()
    )
    if devices_in_use > 0:
        raise ValidationError(
            f"Cannot delete: {devices_in_use} device(s) belong to this network",
            field="id",
        )

    ips_in_use = (
        db.query(IPAddress)
        .filter(IPAddress.network_id == network_id)
        .count()
    )
    if ips_in_use > 0:
        raise ValidationError(
            f"Cannot delete: {ips_in_use} IP address(es) belong to this network",
            field="id",
        )

    db.delete(network)
    db.flush()

def contains_ip(network: Network, ip: str) -> bool:
    try:
        net = ipaddress.IPv4Network(
            f"{network.network_address}/{network.mask}", strict=False
        )
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return addr in net

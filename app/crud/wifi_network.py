from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.device import Device
from app.models.wifi_network import WiFiNetwork

VALID_BANDS = {"2.4", "5", "6"}

VALID_ENCRYPTIONS = {
    "WPA2-PSK/AES",
    "WPA3-PSK/AES",
    "WPA2/WPA3-PSK/AES",
    "WPA-PSK/AES",
    "WEP",
    "Open",
}

def list_by_device(db: Session, device_id: int) -> list[WiFiNetwork]:
    return (
        db.query(WiFiNetwork)
        .filter(WiFiNetwork.device_id == device_id)
        .order_by(WiFiNetwork.ssid)
        .all()
    )

def list_all(db: Session) -> list[WiFiNetwork]:
    return db.query(WiFiNetwork).order_by(WiFiNetwork.ssid).all()

def get_by_id(db: Session, wifi_id: int) -> WiFiNetwork | None:
    return db.get(WiFiNetwork, wifi_id)

def get_by_device_and_ssid(
    db: Session,
    device_id: int,
    ssid: str,
) -> WiFiNetwork | None:
    return (
        db.query(WiFiNetwork)
        .filter(WiFiNetwork.device_id == device_id, WiFiNetwork.ssid == ssid)
        .first()
    )

def _validate(
    ssid: str,
    band: str | None,
    encryption: str | None,
) -> tuple[str, str | None, str | None]:
    ssid = (ssid or "").strip()
    if not ssid:
        raise ValidationError("SSID is required", field="ssid")
    if len(ssid) > 100:
        raise ValidationError("SSID must be at most 100 characters", field="ssid")

    if band is not None and band.strip():
        band = band.strip()
        if band not in VALID_BANDS:
            raise ValidationError(
                f"Invalid band: {band}. Allowed: {', '.join(sorted(VALID_BANDS))}",
                field="band",
            )
    else:
        band = None

    if encryption is not None and encryption.strip():
        encryption = encryption.strip()
        if encryption not in VALID_ENCRYPTIONS:
            raise ValidationError(
                f"Invalid encryption: {encryption}. "
                f"Allowed: {', '.join(sorted(VALID_ENCRYPTIONS))}",
                field="encryption",
            )
    else:
        encryption = None

    return ssid, band, encryption

def create(
    db: Session,
    device_id: int,
    ssid: str,
    band: str | None = None,
    encryption: str | None = None,
    password: str | None = None,
    is_guest: bool = False,
) -> WiFiNetwork:
    if db.get(Device, device_id) is None:
        raise ValidationError("Device not found", field="device_id")

    ssid, band, encryption = _validate(ssid, band, encryption)

    if get_by_device_and_ssid(db, device_id, ssid) is not None:
        raise ValidationError(
            f"Wi-Fi network '{ssid}' already exists on this device",
            field="ssid",
        )

    wifi = WiFiNetwork(
        device_id=device_id,
        ssid=ssid,
        band=band,
        encryption=encryption,
        password=password or None,
        is_guest=is_guest,
    )
    db.add(wifi)
    db.flush()
    return wifi

def update(
    db: Session,
    wifi_id: int,
    ssid: str,
    band: str | None = None,
    encryption: str | None = None,
    password: str | None = None,
    is_guest: bool = False,
) -> WiFiNetwork:
    wifi = get_by_id(db, wifi_id)
    if wifi is None:
        raise ValidationError("Wi-Fi network not found", field="id")

    ssid, band, encryption = _validate(ssid, band, encryption)

    existing = get_by_device_and_ssid(db, wifi.device_id, ssid)
    if existing is not None and existing.id != wifi_id:
        raise ValidationError(
            f"Wi-Fi network '{ssid}' already exists on this device",
            field="ssid",
        )

    wifi.ssid = ssid
    wifi.band = band
    wifi.encryption = encryption
    wifi.password = password or None
    wifi.is_guest = is_guest
    db.flush()
    return wifi

def delete(db: Session, wifi_id: int) -> None:
    wifi = get_by_id(db, wifi_id)
    if wifi is None:
        raise ValidationError("Wi-Fi network not found", field="id")
    db.delete(wifi)
    db.flush()

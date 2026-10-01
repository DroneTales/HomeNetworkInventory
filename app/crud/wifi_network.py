# Home Network Inventory
# Wi-Fi networks CRUD (AP side).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.validation import require_found, validate_choice
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


def list_by_site(db: Session, site_id: int) -> list[WiFiNetwork]:
    return (
        db.query(WiFiNetwork)
        .join(Device, WiFiNetwork.device_id == Device.id)
        .filter(Device.site_id == site_id)
        .order_by(WiFiNetwork.ssid)
        .all()
    )

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
        band = validate_choice(band.strip(), VALID_BANDS, "band", "band")
    else:
        band = None

    if encryption is not None and encryption.strip():
        encryption = validate_choice(
            encryption.strip(), VALID_ENCRYPTIONS, "encryption", "encryption"
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
    require_found(db.get(Device, device_id), "Device", field="device_id")

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
    wifi = require_found(get_by_id(db, wifi_id), "Wi-Fi network")

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
    wifi = require_found(get_by_id(db, wifi_id), "Wi-Fi network")
    db.delete(wifi)
    db.flush()

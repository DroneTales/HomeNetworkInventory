import ipaddress
import re

from app.core.exceptions import ValidationError

# MAC вида AA:BB:CC:DD:EE:FF или AA-BB-CC-DD-EE-FF
MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")

# Hostname: латиница, цифры, дефис, подчёркивание, точка. Начинается и заканчивается
# буквой или цифрой. Максимум 100 символов. Пробелы запрещены.
HOSTNAME_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$")


def validate_ip(value: str, field: str = "ip") -> str:
    """Проверяет, что строка — валидный IPv4 или IPv6. Возвращает нормализованную строку."""
    if value is None or not value.strip():
        raise ValidationError("IP address is required", field=field)
    try:
        addr = ipaddress.ip_address(value.strip())
    except ValueError:
        raise ValidationError(f"Invalid IP address: {value}", field=field)
    return str(addr)


def validate_ipv4(value: str, field: str = "ip") -> str:
    """Проверяет, что строка — валидный IPv4. Возвращает нормализованную строку."""
    if value is None or not value.strip():
        raise ValidationError("IPv4 address is required", field=field)
    try:
        addr = ipaddress.IPv4Address(value.strip())
    except ValueError:
        raise ValidationError(f"Invalid IPv4 address: {value}", field=field)
    return str(addr)


def validate_mask(value: str, field: str = "mask") -> str:
    """Проверяет, что маска — валидная маска подсети IPv4."""
    if value is None or not value.strip():
        raise ValidationError("Mask is required", field=field)
    try:
        # Проверим через IPv4Network — она сама отвалидирует маску.
        ipaddress.IPv4Network(f"0.0.0.0/{value.strip()}", strict=False)
    except ValueError:
        raise ValidationError(f"Invalid mask: {value}", field=field)
    return value.strip()


def validate_mac(value: str, field: str = "mac") -> str:
    """Проверяет MAC-адрес. Возвращает нормализованный в верхнем регистре с двоеточиями."""
    if value is None or not value.strip():
        raise ValidationError("MAC address is required", field=field)
    raw = value.strip()
    if not MAC_RE.match(raw):
        raise ValidationError(f"Invalid MAC address: {value}", field=field)
    # Нормализуем: убираем разделители, разбиваем по 2, собираем через двоеточие.
    hex_only = re.sub(r"[:-]", "", raw).upper()
    return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))


def validate_hostname(value: str, field: str = "hostname") -> str:
    """Проверяет hostname: без пробелов, только допустимые символы."""
    if value is None or not value.strip():
        raise ValidationError("Hostname is required", field=field)
    raw = value.strip()
    if not HOSTNAME_RE.match(raw):
        raise ValidationError(
            f"Invalid hostname: {value}. Only letters, digits, dots, dashes and underscores "
            "are allowed, no spaces.",
            field=field,
        )
    return raw


def validate_same_subnet(
    ip: str,
    mask: str,
    other_ip: str,
    field: str = "gateway",
    other_name: str = "gateway",
) -> None:
    """Проверяет, что два IP находятся в одной подсети с данной маской.

    Используется для проверки, что gateway и IP — в одной подсети.
    """
    try:
        net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
        other = ipaddress.IPv4Address(other_ip)
    except ValueError as e:
        raise ValidationError(f"Cannot compare subnets: {e}", field=field)

    if other not in net:
        raise ValidationError(
            f"{other_name.capitalize()} {other_ip} is not in the same subnet as {ip}/{mask}",
            field=field,
        )


def is_ip_in_range(ip: str, start: str, end: str) -> bool:
    """Проверяет, попадает ли IP в диапазон [start, end] включительно."""
    try:
        addr = ipaddress.IPv4Address(ip)
        lo = ipaddress.IPv4Address(start)
        hi = ipaddress.IPv4Address(end)
    except ValueError:
        return False
    return lo <= addr <= hi


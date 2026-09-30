def to_int(value) -> int | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None

def parse_ipv4(ip_str: str) -> tuple[int, int, int, int] | None:
    if not ip_str:
        return None
    parts = ip_str.split(".")
    if len(parts) != 4:
        return None
    try:
        octets = tuple(int(p) for p in parts)
    except ValueError:
        return None
    if any(o < 0 or o > 255 for o in octets):
        return None
    return octets

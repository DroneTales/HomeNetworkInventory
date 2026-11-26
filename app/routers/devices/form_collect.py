# Home Network Inventory
# Devices UI: form payload collectors.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.constants import DHCP_POOL_TYPE_DYNAMIC, IFACE_TYPE_ETHERNET, IP_TYPE_STATIC, PF_PROTOCOL_TCP
from app.core.utils import to_int

def _parse_mac_filter_data(raw: str) -> list[dict]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        device_id = to_int(item.get("device"))
        if device_id is None:
            continue
        result.append({
            "id": to_int(item.get("id")),
            "device": device_id,
            "active": bool(item.get("active", True)),
        })
    return result

def _collect_interfaces(form) -> list[dict]:
    ids = form.getlist("interface_id")
    names = form.getlist("interface_name")
    types = form.getlist("interface_type")
    macs = form.getlist("interface_mac")
    bands = form.getlist("interface_band")
    addresses = form.getlist("interface_address")
    masks = form.getlist("interface_mask")
    address_types = form.getlist("interface_address_type")
    gateways = form.getlist("interface_gateway")
    dns_list = form.getlist("interface_dns")
    wifi_links = form.getlist("interface_connected_wifi")
    network_ids = form.getlist("interface_network_id")

    result = []
    for i, name in enumerate(names):
        name = (name or "").strip()
        if not name:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        iface_type = (types[i] if i < len(types) else IFACE_TYPE_ETHERNET).strip().lower()
        mac = (macs[i] if i < len(macs) else "").strip() or None
        band = (bands[i] if i < len(bands) else "").strip() or None

        address = (addresses[i] if i < len(addresses) else "").strip() or None
        mask = (masks[i] if i < len(masks) else "").strip() or None
        address_type = (address_types[i] if i < len(address_types) else IP_TYPE_STATIC).strip().lower()
        gateway = (gateways[i] if i < len(gateways) else "").strip() or None
        dns = (dns_list[i] if i < len(dns_list) else "").strip() or None
        connected_wifi = (wifi_links[i] if i < len(wifi_links) else "").strip() or None
        network_id = to_int(network_ids[i] if i < len(network_ids) else None)

        result.append({
            "id": item_id,
            "name": name,
            "type": iface_type,
            "mac": mac,
            "band": band,
            "address": address,
            "mask": mask,
            "address_type": address_type,
            "gateway": gateway,
            "dns": dns,
            "connected_wifi_network_id": connected_wifi,
            "network_id": network_id,
        })

    return result

def _collect_ports(form) -> list[dict]:
    ids = form.getlist("port_id")
    names = form.getlist("port_name")
    interface_ids = form.getlist("port_interface_id")
    descriptions = form.getlist("port_description")

    result = []
    for i, name in enumerate(names):
        name = (name or "").strip()
        if not name:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        interface_id = (interface_ids[i] if i < len(interface_ids) else "").strip() or None
        description = (descriptions[i] if i < len(descriptions) else "").strip() or None

        result.append({
            "id": item_id,
            "name": name,
            "interface_id": interface_id,
            "description": description,
        })

    return result

def _collect_wifi_networks(form) -> list[dict]:
    ids = form.getlist("wifi_id")
    ssids = form.getlist("wifi_ssid")
    iface_ids = form.getlist("wifi_interface_id")
    encryptions = form.getlist("wifi_encryption")
    passwords = form.getlist("wifi_password")
    guests = form.getlist("wifi_is_guest")
    mac_filter_modes = form.getlist("wifi_mac_filter")
    mac_filter_data = form.getlist("wifi_mac_filter_data")

    result = []
    for i, ssid in enumerate(ssids):
        ssid = (ssid or "").strip()
        if not ssid:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        interface_id = (iface_ids[i] if i < len(iface_ids) else "").strip() or None
        encryption = (encryptions[i] if i < len(encryptions) else "").strip() or None
        password = (passwords[i] if i < len(passwords) else "").strip() or None
        guest = (guests[i] if i < len(guests) else "") == "on"
        mac_filter = to_int(mac_filter_modes[i] if i < len(mac_filter_modes) else "0") or 0
        raw_filters = mac_filter_data[i] if i < len(mac_filter_data) else ""

        result.append({
            "id": item_id,
            "ssid": ssid,
            "interface_id": interface_id,
            "encryption": encryption,
            "password": password,
            "is_guest": guest,
            "mac_filter": mac_filter,
            "mac_filters": _parse_mac_filter_data(raw_filters),
        })

    return result

def _collect_dhcp_pools(form) -> list[dict]:
    ids = form.getlist("dhcp_id")
    names = form.getlist("dhcp_name")
    types = form.getlist("dhcp_type")
    starts = form.getlist("dhcp_start_ip")
    ends = form.getlist("dhcp_end_ip")
    gateways = form.getlist("dhcp_gateway")
    dns_list = form.getlist("dhcp_dns")
    descriptions = form.getlist("dhcp_description")

    result = []
    for i, start in enumerate(starts):
        start = (start or "").strip()
        end = (ends[i] if i < len(ends) else "").strip()
        if not start and not end:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        result.append({
            "id": item_id,
            "name": (names[i] if i < len(names) else "").strip() or None,
            "type": (types[i] if i < len(types) else DHCP_POOL_TYPE_DYNAMIC).strip().lower(),
            "start_ip": start,
            "end_ip": end,
            "gateway": (gateways[i] if i < len(gateways) else "").strip() or None,
            "dns": (dns_list[i] if i < len(dns_list) else "").strip() or None,
            "description": (descriptions[i] if i < len(descriptions) else "").strip() or None,
        })

    return result

def _collect_credentials(form) -> list[dict]:
    ids = form.getlist("credential_id")
    type_ids = form.getlist("credential_type_id")
    usernames = form.getlist("credential_username")
    passwords = form.getlist("credential_password")
    descriptions = form.getlist("credential_description")

    result = []
    max_len = max(len(usernames), len(passwords), len(type_ids), len(ids))

    for i in range(max_len):
        item_id = to_int(ids[i] if i < len(ids) else None)
        type_id = to_int(type_ids[i] if i < len(type_ids) else None)
        username = (usernames[i] if i < len(usernames) else "").strip() or None
        password = (passwords[i] if i < len(passwords) else "").strip() or None
        description = (descriptions[i] if i < len(descriptions) else "").strip() or None

        if type_id is None and username is None and password is None:
            continue

        result.append({
            "id": item_id,
            "type_id": type_id,
            "username": username,
            "password": password,
            "description": description,
        })

    return result

def _collect_services(form) -> list[dict]:
    ids = form.getlist("service_id")
    names = form.getlist("service_name")
    protocols = form.getlist("service_protocol")
    urls = form.getlist("service_url")
    usernames = form.getlist("service_username")
    passwords = form.getlist("service_password")
    descriptions = form.getlist("service_description")

    result = []
    for i, name in enumerate(names):
        name = (name or "").strip()
        if not name:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        protocol = (protocols[i] if i < len(protocols) else "").strip() or None
        url = (urls[i] if i < len(urls) else "").strip() or None
        username = (usernames[i] if i < len(usernames) else "").strip() or None
        password = (passwords[i] if i < len(passwords) else "").strip() or None
        description = (descriptions[i] if i < len(descriptions) else "").strip() or None

        result.append({
            "id": item_id,
            "name": name,
            "protocol": protocol,
            "url": url,
            "username": username,
            "password": password,
            "description": description,
        })

    return result

def _collect_port_forwards(form) -> list[dict]:
    ids = form.getlist("pf_id")
    ext_starts = form.getlist("pf_external_start")
    ext_ends = form.getlist("pf_external_end")
    protocols = form.getlist("pf_protocol")
    target_types = form.getlist("pf_target_type")
    internal_device_ids = form.getlist("pf_internal_device_id")
    internal_ip_manual_list = form.getlist("pf_internal_ip_manual")
    internal_starts = form.getlist("pf_internal_start")
    internal_ends = form.getlist("pf_internal_end")
    descriptions = form.getlist("pf_description")
    nat_loopbacks = form.getlist("pf_nat_loopback")

    active_flags = set()
    for idx, v in enumerate(form.getlist("pf_is_active")):
        if v == "on":
            active_flags.add(idx)
    active_by_id = {}
    for idx, item_id in enumerate(ids):
        if item_id and item_id.strip() and idx in active_flags:
            active_by_id[item_id.strip()] = True

    max_len = max(len(ext_starts), len(ids))
    result = []
    for i in range(max_len):
        ext_start = (ext_starts[i] if i < len(ext_starts) else "").strip()
        ext_end = (ext_ends[i] if i < len(ext_ends) else "").strip()
        if not ext_start and not ext_end:
            continue

        item_id = to_int(ids[i] if i < len(ids) else None)
        target_type = (target_types[i] if i < len(target_types) else "device").strip().lower()
        internal_device_id = to_int(internal_device_ids[i] if i < len(internal_device_ids) else None)
        internal_ip_manual = (internal_ip_manual_list[i] if i < len(internal_ip_manual_list) else "").strip() or None

        if target_type == "ip":
            internal_device_id = None
        else:
            internal_ip_manual = None

        is_active = (
            active_by_id.get(str(item_id), False) if item_id else i in active_flags
        )

        result.append({
            "id": item_id,
            "external_port_start": ext_start,
            "external_port_end": ext_end,
            "protocol": (protocols[i] if i < len(protocols) else PF_PROTOCOL_TCP).strip().lower(),
            "internal_device_id": internal_device_id,
            "internal_ip_manual": internal_ip_manual,
            "internal_port_start": (internal_starts[i] if i < len(internal_starts) else "").strip(),
            "internal_port_end": (internal_ends[i] if i < len(internal_ends) else "").strip(),
            "description": (descriptions[i] if i < len(descriptions) else "").strip() or None,
            "nat_loopback": (nat_loopbacks[i] if i < len(nat_loopbacks) else "None").strip() or "None",
            "is_active": is_active,
        })
    return result

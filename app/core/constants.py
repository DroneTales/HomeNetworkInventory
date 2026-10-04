# Home Network Inventory
# Shared string constants (roles, types, protocols).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

ROLE_ADMIN = "admin"
ROLE_USER = "user"
VALID_ROLES = {ROLE_ADMIN, ROLE_USER}

PF_PROTOCOL_TCP = "tcp"
PF_PROTOCOL_UDP = "udp"
PF_PROTOCOL_BOTH = "both"
VALID_PF_PROTOCOLS = {PF_PROTOCOL_TCP, PF_PROTOCOL_UDP, PF_PROTOCOL_BOTH}

IFACE_TYPE_ETHERNET = "ethernet"
IFACE_TYPE_WIFI = "wifi"
IFACE_TYPE_WIFI_AP = "wifi_ap"
IFACE_TYPE_WAN = "wan"
IFACE_TYPE_VIRTUAL = "virtual"
IFACE_TYPE_PORT = "port"
VALID_IFACE_TYPES = {
    IFACE_TYPE_ETHERNET,
    IFACE_TYPE_WIFI,
    IFACE_TYPE_WIFI_AP,
    IFACE_TYPE_WAN,
    IFACE_TYPE_VIRTUAL,
    IFACE_TYPE_PORT,
}

VALID_BANDS = {"2.4", "5", "6"}

IP_TYPE_STATIC = "static"
IP_TYPE_DHCP = "dhcp"
IP_TYPE_EXTERNAL = "external"
IP_TYPE_RESERVED = "reserved"
VALID_IP_ADDRESS_TYPES = {
    IP_TYPE_STATIC,
    IP_TYPE_DHCP,
    IP_TYPE_EXTERNAL,
    IP_TYPE_RESERVED,
}
MAC_REQUIRED_IP_TYPES = {IP_TYPE_DHCP, IP_TYPE_RESERVED}

DHCP_POOL_TYPE_DYNAMIC = "dynamic"
DHCP_POOL_TYPE_FIXED = "fixed"
VALID_DHCP_POOL_TYPES = {DHCP_POOL_TYPE_DYNAMIC, DHCP_POOL_TYPE_FIXED}

CONNECTION_TYPE_PHYSICAL = "physical"
CONNECTION_TYPE_LOGICAL = "logical"
VALID_CONNECTION_TYPES = {CONNECTION_TYPE_PHYSICAL, CONNECTION_TYPE_LOGICAL}

VALID_SERVICE_PROTOCOLS = {"http", "https", "rtsp", "ssh", "other"}

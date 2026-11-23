# Home Network Inventory
# XLSX and CSV export of devices and connections.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
import zipfile
from typing import Callable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.core.utils import parse_ipv4
from app.crud import connection as crud_connection
from app.crud import device as crud_device

def _sorted_devices(db: Session, site_id: int):
    devices = crud_device.list_all(db, site_id)

    def sort_key(d) -> tuple:
        parsed = []
        for iface in d.interfaces:
            for ip in iface.ip_addresses:
                octets = parse_ipv4(ip.address)
                if octets is not None:
                    parsed.append(octets)
        if not parsed:
            return (1, (0, 0, 0, 0))
        return (0, min(parsed))

    devices.sort(key=sort_key)
    return devices

def device_rows(db: Session, site_id: int, t: Callable) -> list[list]:
    rows = []
    for d in _sorted_devices(db, site_id):
        ips = []
        macs = []
        for iface in d.interfaces:
            for ip in iface.ip_addresses:
                if ip.address:
                    ips.append(ip.address)
            if iface.mac:
                macs.append(iface.mac)
        rows.append([
            d.location.name if d.location else "",
            d.hostname or "",
            d.human_readable_name or "",
            d.device_type.name if d.device_type else "",
            d.vendor.name if d.vendor else "",
            d.model.name if d.model else "",
            "\n".join(ips),
            "\n".join(macs),
        ])
    return rows

def connection_rows(db: Session, site_id: int) -> list[list]:
    connections = crud_connection.list_all(db, site_id)
    rows = []
    for c in connections:
        sp = c.source_port
        tp = c.target_port
        cable = c.cable_type or ""
        # source -> target
        rows.append([
            sp.device.location.name if sp.device.location else "",
            sp.device.hostname or "",
            sp.name or "",
            tp.device.location.name if tp.device.location else "",
            tp.device.hostname or "",
            tp.name or "",
            cable,
        ])
        # target -> source (duplicate, as on the Connections page)
        rows.append([
            tp.device.location.name if tp.device.location else "",
            tp.device.hostname or "",
            tp.name or "",
            sp.device.location.name if sp.device.location else "",
            sp.device.hostname or "",
            sp.name or "",
            cable,
        ])
    # group by source device, then by port
    rows.sort(key=lambda r: (
        (r[0] or "").lower(),
        (r[1] or "").lower(),
        (r[2] or "").lower(),
    ))
    return rows

def _headers(t: Callable) -> tuple[list[str], list[str]]:
    devices = [
        t("devices.list.location"),
        t("devices.list.hostname"),
        t("devices.list.name"),
        t("devices.list.type"),
        t("devices.list.vendor"),
        t("devices.list.model"),
        t("devices.list.local_ip"),
        t("devices.list.mac"),
    ]
    connections = [
        t("export.connections.source_location"),
        t("export.connections.source_device"),
        t("export.connections.source_port"),
        t("export.connections.target_location"),
        t("export.connections.target_device"),
        t("export.connections.target_port"),
        t("export.connections.cable"),
    ]
    return devices, connections

def to_xlsx(db: Session, site_id: int, t: Callable) -> bytes:
    dev_h, conn_h = _headers(t)
    dev_rows = device_rows(db, site_id, t)
    conn_rows = connection_rows(db, site_id)

    wb = Workbook()
    ws = wb.active
    ws.title = t("export.sheet.devices")
    ws.append(dev_h)
    for row in dev_rows:
        ws.append(row)
    _style_sheet(ws, dev_h)

    ws2 = wb.create_sheet(t("export.sheet.connections"))
    ws2.append(conn_h)
    for row in conn_rows:
        ws2.append(row)
    _style_sheet(ws2, conn_h)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def _style_sheet(ws, headers: list[str]) -> None:
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    for col_idx, header in enumerate(headers, start=1):
        max_len = len(header)
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value is not None:
                    for line in str(cell.value).split("\n"):
                        max_len = max(max_len, len(line))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 40)

def _csv_bytes(headers: list[str], rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")

def to_csv_zip(db: Session, site_id: int, t: Callable, site_name: str) -> bytes:
    dev_h, conn_h = _headers(t)
    dev_csv = _csv_bytes(dev_h, device_rows(db, site_id, t))
    conn_csv = _csv_bytes(conn_h, connection_rows(db, site_id))

    slug = "".join(c if c.isalnum() else "_" for c in site_name.lower()).strip("_") or "site"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}_devices.csv", dev_csv)
        zf.writestr(f"{slug}_connections.csv", conn_csv)
    return buf.getvalue()

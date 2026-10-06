# Home Network Inventory
# Full-database JSON export and import.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, insert, text
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.database import Base

EXPORT_VERSION = 1

_BYTES_MARK = "__bytes_b64__"
_DT_MARK = "__datetime__"

def _encode_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {_BYTES_MARK: base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        return {_DT_MARK: value.isoformat()}
    return value

def _decode_value(value: Any) -> Any:
    if isinstance(value, dict):
        if _BYTES_MARK in value:
            return base64.b64decode(value[_BYTES_MARK])
        if _DT_MARK in value:
            return datetime.fromisoformat(value[_DT_MARK])
    return value

def _tables_in_fk_order():
    return list(Base.metadata.sorted_tables)

def export_all(db: Session) -> dict:
    tables: dict[str, list[dict]] = {}
    for table in _tables_in_fk_order():
        cols = list(table.columns.keys())
        rows = []
        result = db.execute(table.select())
        for row in result.mappings():
            rows.append({c: _encode_value(row[c]) for c in cols})
        tables[table.name] = rows
    return {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": tables,
    }

def import_all(db: Session, data: dict) -> None:
    if not isinstance(data, dict):
        raise ValidationError("Invalid file format")
    if data.get("version") != EXPORT_VERSION:
        raise ValidationError("Unsupported export version")
    tables_data = data.get("tables")
    if not isinstance(tables_data, dict):
        raise ValidationError("Missing 'tables' section")

    tables = _tables_in_fk_order()

    is_sqlite = db.bind is not None and db.bind.dialect.name == "sqlite"
    if is_sqlite:
        db.execute(text("PRAGMA foreign_keys=OFF"))

    for table in reversed(tables):
        db.execute(delete(table))

    for table in tables:
        rows = tables_data.get(table.name) or []
        if not rows:
            continue
        cols = list(table.columns.keys())
        payload = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValidationError(f"Invalid row in table '{table.name}'")
            payload.append({c: _decode_value(row.get(c)) for c in cols})
        if payload:
            db.execute(insert(table), payload)

    if is_sqlite:
        try:
            db.execute(text("DELETE FROM sqlite_sequence"))
        except Exception:
            pass
        db.execute(text("PRAGMA foreign_keys=ON"))

    db.commit()

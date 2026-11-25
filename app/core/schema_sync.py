# Home Network Inventory
# Schema diff and safe ADD COLUMN migrations.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.engine import Engine

from app.database import Base


@dataclass
class ColumnDiff:
    table: str
    name: str
    type_sql: str
    nullable: bool
    default_sql: str | None
    default_value: Any
    guessed: bool


@dataclass
class ExtraColumn:
    table: str
    name: str
    type_sql: str


@dataclass
class SchemaDiff:
    missing_columns: list[ColumnDiff] = field(default_factory=list)
    extra_columns: list[ExtraColumn] = field(default_factory=list)
    missing_tables: list[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return not self.missing_columns and not self.missing_tables


def _sql_type(col, dialect) -> str:
    try:
        return col.type.compile(dialect=dialect)
    except Exception:
        return "VARCHAR(255)"


def _quote_default(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if value.upper() == "CURRENT_TIMESTAMP":
            return "CURRENT_TIMESTAMP"
        return "'" + value.replace("'", "''") + "'"
    return "'" + str(value).replace("'", "''") + "'"


def _resolve_default(col, dialect) -> tuple[str | None, Any, bool]:
    if col.server_default is not None:
        arg = col.server_default.arg
        text = getattr(arg, "text", None)
        if text is not None:
            return str(text), None, False
        if isinstance(arg, str):
            return arg, None, False

    if col.default is not None:
        arg = col.default.arg
        if callable(arg):
            try:
                value = arg(None)
            except Exception:
                value = None
            if value is not None:
                return _quote_default(value), value, False
        else:
            return _quote_default(arg), arg, False

    if col.nullable:
        return None, None, False

    t = col.type
    if isinstance(t, Boolean):
        return "0", 0, True
    if isinstance(t, (Integer,)):
        return "0", 0, True
    if isinstance(t, (Float, Numeric)):
        return "0", 0, True
    if isinstance(t, DateTime):
        return "CURRENT_TIMESTAMP", None, True
    if isinstance(t, (String, Text)):
        return "''", "", True
    return None, None, True


def get_schema_diff(engine: Engine) -> SchemaDiff:
    diff = SchemaDiff()
    inspector = sa_inspect(engine)
    dialect = engine.dialect

    existing_tables = set(inspector.get_table_names())

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            diff.missing_tables.append(table_name)
            continue

        existing_cols = {c["name"]: c for c in inspector.get_columns(table_name)}

        for col in table.columns:
            if col.name in existing_cols:
                continue
            type_sql = _sql_type(col, dialect)
            default_sql, default_value, guessed = _resolve_default(col, dialect)
            diff.missing_columns.append(ColumnDiff(
                table=table_name,
                name=col.name,
                type_sql=type_sql,
                nullable=bool(col.nullable),
                default_sql=default_sql,
                default_value=default_value,
                guessed=guessed,
            ))

        model_col_names = {c.name for c in table.columns}
        for name, info in existing_cols.items():
            if name not in model_col_names:
                diff.extra_columns.append(ExtraColumn(
                    table=table_name,
                    name=name,
                    type_sql=str(info.get("type") or ""),
                ))

    return diff


def apply_missing_columns(engine: Engine, diff: SchemaDiff) -> list[str]:
    applied = []
    with engine.begin() as conn:
        for c in diff.missing_columns:
            parts = [f'"{c.name}"', c.type_sql]
            if c.default_sql is not None:
                parts.append(f"DEFAULT {c.default_sql}")
            if not c.nullable:
                parts.append("NOT NULL")
            sql = f'ALTER TABLE "{c.table}" ADD COLUMN ' + " ".join(parts)
            conn.exec_driver_sql(sql)
            applied.append(f"{c.table}.{c.name}")
    return applied


def _devices_needs_rebuild(engine: Engine) -> bool:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(devices)").fetchall()
    cols = {r[1]: r for r in rows}
    if "hostname" not in cols or "human_readable_name" not in cols:
        return False
    hostname_notnull = bool(cols["hostname"][3])
    name_nullable = not bool(cols["human_readable_name"][3])
    return hostname_notnull or name_nullable


def _backup_database(engine: Engine) -> str | None:
    db_path = engine.url.database
    if not db_path or db_path == ":memory:":
        return None
    p = Path(db_path)
    if not p.exists():
        return None
    backup = p.with_name(p.name + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(p, backup)
    return str(backup)


def _dedupe_device_names(conn) -> int:
    rows = conn.exec_driver_sql(
        "SELECT id, site_id, human_readable_name FROM devices "
        "WHERE human_readable_name IS NOT NULL AND TRIM(human_readable_name) <> '' "
        "ORDER BY site_id, id"
    ).fetchall()
    used: dict[int, set[str]] = {}
    for _id, site, name in rows:
        used.setdefault(site, set()).add(name)
    seen: set[tuple[int, str]] = set()
    renamed = 0
    for did, site, name in rows:
        key = (site, name)
        if key not in seen:
            seen.add(key)
            continue
        n = 2
        while True:
            suffix = f" ({n})"
            base = name if len(name) + len(suffix) <= 60 else name[: 60 - len(suffix)]
            candidate = base + suffix
            if candidate not in used[site]:
                break
            n += 1
        conn.exec_driver_sql(
            "UPDATE devices SET human_readable_name = ? WHERE id = ?",
            (candidate, did),
        )
        used[site].add(candidate)
        renamed += 1
    return renamed


def _rebuild_devices(conn) -> None:
    conn.exec_driver_sql("""
        CREATE TABLE devices_new (
            id INTEGER NOT NULL,
            site_id INTEGER NOT NULL,
            hostname VARCHAR(100),
            human_readable_name VARCHAR(60) NOT NULL,
            remarks VARCHAR,
            device_type_id INTEGER,
            vendor_id INTEGER,
            model_id INTEGER,
            location_id INTEGER,
            is_active BOOLEAN NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            description VARCHAR(255),
            PRIMARY KEY (id),
            FOREIGN KEY(site_id) REFERENCES sites (id) ON DELETE CASCADE,
            FOREIGN KEY(device_type_id) REFERENCES device_types (id),
            FOREIGN KEY(vendor_id) REFERENCES vendors (id),
            FOREIGN KEY(model_id) REFERENCES models (id),
            FOREIGN KEY(location_id) REFERENCES locations (id)
        )
    """)
    conn.exec_driver_sql("""
        INSERT INTO devices_new
            (id, site_id, hostname, human_readable_name, remarks, device_type_id,
             vendor_id, model_id, location_id, is_active, created_at, updated_at, description)
        SELECT id, site_id, hostname, human_readable_name, remarks, device_type_id,
               vendor_id, model_id, location_id, is_active, created_at, updated_at, description
        FROM devices
    """)
    conn.exec_driver_sql("DROP TABLE devices")
    conn.exec_driver_sql("ALTER TABLE devices_new RENAME TO devices")
    conn.exec_driver_sql("CREATE INDEX ix_devices_hostname ON devices (hostname)")
    conn.exec_driver_sql("CREATE INDEX ix_devices_site_id ON devices (site_id)")


def apply_data_migrations(engine: Engine) -> list[str]:
    applied: list[str] = []
    if not _devices_needs_rebuild(engine):
        return applied

    backup = _backup_database(engine)
    if backup:
        applied.append(f"backup: {backup}")

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            conn.exec_driver_sql("BEGIN")
            conn.exec_driver_sql(
                "UPDATE devices SET human_readable_name = hostname "
                "WHERE (human_readable_name IS NULL OR TRIM(human_readable_name) = '') "
                "AND hostname IS NOT NULL AND TRIM(hostname) <> ''"
            )
            filled = conn.exec_driver_sql("SELECT changes()").scalar() or 0
            if filled:
                applied.append(f"devices: filled {filled} empty name(s) from hostname")

            renamed = _dedupe_device_names(conn)
            if renamed:
                applied.append(f"devices: renamed {renamed} duplicate name(s)")

            _rebuild_devices(conn)
            applied.append("devices: rebuilt (hostname nullable, human_readable_name NOT NULL)")
            conn.exec_driver_sql("COMMIT")
        except Exception:
            conn.exec_driver_sql("ROLLBACK")
            raise
        finally:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    return applied

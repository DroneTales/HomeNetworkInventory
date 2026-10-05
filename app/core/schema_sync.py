# Home Network Inventory
# Schema diff and safe ADD COLUMN migrations.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass, field
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

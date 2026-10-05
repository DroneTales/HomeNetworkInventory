# Home Network Inventory
# Standalone migration CLI: add missing columns to bring the DB up to date.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import shutil
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine

from app import models  # noqa: F401
from app.config import settings
from app.core.schema_sync import apply_missing_columns, get_schema_diff
from app.database import Base


def _db_path() -> Path | None:
    url = settings.database_url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return None
    path = url[len(prefix):]
    return Path(path).resolve()


def _backup_db(path: Path) -> Path | None:
    if not path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(path.name + f".before-migrate-{ts}")
    shutil.copy2(path, dest)
    return dest


def _print_diff(diff) -> None:
    if diff.missing_tables:
        print("Missing tables:")
        for t in diff.missing_tables:
            print(f"  {t}")
        print()

    if diff.missing_columns:
        print("Missing columns:")
        for c in diff.missing_columns:
            flags = []
            if not c.nullable:
                flags.append("NOT NULL")
            if c.default_sql is not None:
                flags.append(f"DEFAULT {c.default_sql}")
            if c.guessed:
                flags.append("(guessed)")
            suffix = (" " + " ".join(flags)) if flags else ""
            print(f"  {c.table}.{c.name} {c.type_sql}{suffix}")
        print()

    if diff.extra_columns:
        print("Extra columns in DB (not touched):")
        for c in diff.extra_columns:
            print(f"  {c.table}.{c.name} {c.type_sql}")
        print()


def _confirm_guessed(diff) -> bool:
    guessed = [c for c in diff.missing_columns if c.guessed]
    if not guessed:
        return True
    print("The following NOT NULL columns have no default in the model.")
    print("A best-guess default will be used. Review the values below:")
    print()
    for c in guessed:
        value = c.default_value
        if c.default_sql == "CURRENT_TIMESTAMP":
            value = "CURRENT_TIMESTAMP"
        print(f"  {c.table}.{c.name}  ->  {value!r}")
    print()
    answer = input("Continue? [y/N]: ").strip().lower()
    return answer in ("y", "yes")


def _confirm_extras(diff) -> bool:
    if not diff.extra_columns:
        return True
    print("Extra columns exist in the database but are not part of the current model.")
    print("They will NOT be removed automatically.")
    print("If you want them gone, back up the DB and drop them manually.")
    print()
    answer = input("Proceed with adding missing columns? [y/N]: ").strip().lower()
    return answer in ("y", "yes")


def main() -> int:
    db_path = _db_path()
    engine = create_engine(settings.database_url, future=True)

    Base.metadata.create_all(engine)

    diff = get_schema_diff(engine)

    if diff.is_ok and not diff.extra_columns:
        print("Database schema is up to date. Nothing to do.")
        return 0

    _print_diff(diff)

    if diff.missing_tables:
        print("Missing tables were created by Base.metadata.create_all().")
        print()

    if not diff.missing_columns:
        print("No missing columns to add.")
        return 0

    if not _confirm_extras(diff):
        print("Aborted.")
        return 1
    if not _confirm_guessed(diff):
        print("Aborted.")
        return 1

    if db_path is not None:
        dest = _backup_db(db_path)
        if dest is not None:
            print(f"Backup written: {dest}")
        else:
            print("Database file not found; skipping backup.")

    applied = apply_missing_columns(engine, diff)
    print()
    print(f"Applied {len(applied)} column(s):")
    for item in applied:
        print(f"  {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

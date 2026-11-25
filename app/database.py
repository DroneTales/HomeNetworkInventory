# Home Network Inventory
# SQLAlchemy engine, session factory, Base declarative.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    echo=False,
)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_database_path() -> None:
    url = settings.database_url
    if not url.startswith("sqlite"):
        return

    path_part = url.replace("sqlite:///", "", 1)

    if path_part.startswith(":memory:"):
        return

    db_path = Path(path_part).resolve()
    parent = db_path.parent

    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    if not os.access(parent, os.W_OK):
        raise RuntimeError(
            f"Cannot write to database directory: {parent}"
        )

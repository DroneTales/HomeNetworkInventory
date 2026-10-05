# Home Network Inventory
# FastAPI application entry point and route wiring.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import models  # noqa: F401
from app.config import settings
from app.core.bootstrap import ensure_default_admin
from app.core.deps import get_current_site, require_user
from app.core.i18n import load_translations
from app.core.middleware import CurrentSiteMiddleware
from app.core.schema_sync import get_schema_diff
from app.database import Base, check_database_path, engine, get_db
from app.models.user import User
from app.routers import (
    auth,
    connections,
    devices,
    help,
    profile,
    reference,
    reference_ui,
    sites,
    topology,
    users,
)

BASE_DIR = Path(__file__).resolve().parent

def _check_schema() -> None:
    diff = get_schema_diff(engine)
    if diff.is_ok:
        if diff.extra_columns:
            print("WARNING: extra columns in database (not used by the current model):")
            for c in diff.extra_columns:
                print(f"  {c.table}.{c.name} {c.type_sql}")
        return

    print("")
    print("=" * 64)
    print("  DATABASE SCHEMA IS OUT OF DATE")
    print("=" * 64)
    if diff.missing_tables:
        print("Missing tables:")
        for t in diff.missing_tables:
            print(f"  {t}")
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
    print("")
    print("Run the migration script to bring the database up to date:")
    print("  Windows:     migrate.bat")
    print("  Linux/macOS: ./migrate.command")
    print("  From source: python -m app.migrate")
    print("=" * 64)
    print("")
    sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_database_path()
    Base.metadata.create_all(bind=engine)
    _check_schema()
    ensure_default_admin()
    load_translations()
    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(CurrentSiteMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="hni_session",
    same_site="lax",
    https_only=getattr(settings, "cookie_secure", True),
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(auth.router)
app.include_router(sites.router)
app.include_router(reference.router)
app.include_router(reference_ui.router)
app.include_router(devices.router)
app.include_router(connections.router)
app.include_router(users.router)
app.include_router(profile.router)
app.include_router(help.router)
app.include_router(topology.router)

@app.get("/")
def root(
    request: Request,
    user: User = Depends(require_user),
    db=Depends(get_db),
):
    if user.must_change_password:
        return RedirectResponse("/change-password", status_code=303)

    site = get_current_site(request, user, db)
    if site is None:
        return RedirectResponse("/sites", status_code=303)

    return RedirectResponse("/devices", status_code=303)

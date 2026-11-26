# Home Network Inventory
# FastAPI application entry point and route wiring.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
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
from app.core.logging import setup_logging
from app.core.middleware import CurrentSiteMiddleware
from app.core.schema_sync import (
    apply_data_migrations,
    apply_missing_columns,
    apply_missing_indexes,
    backup_database,
    devices_needs_rebuild,
    get_schema_diff,
)
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

logger = logging.getLogger(__name__)

def _check_schema() -> None:
    diff = get_schema_diff(engine)

    # Back up the database before any schema change
    if diff.missing_tables or diff.missing_columns or devices_needs_rebuild(engine):
        backup = backup_database(engine)
        if backup:
            logger.info("Database backed up to %s", backup)

    # Auto-apply missing tables and columns
    applied = []
    if diff.missing_tables:
        Base.metadata.create_all(bind=engine)
        applied.extend(f"table: {t}" for t in diff.missing_tables)
    
    if diff.missing_columns:
        applied_cols = apply_missing_columns(engine, diff)
        applied.extend(f"column: {c}" for c in applied_cols)

    applied.extend(f"index: {i}" for i in apply_missing_indexes(engine))
    applied.extend(apply_data_migrations(engine))
    
    if applied:
        logger.info("Database schema auto-migrated:")
        for a in applied:
            logger.info("  + %s", a)

        # Re-check to ensure everything is ok now
        diff = get_schema_diff(engine)
        if not diff.is_ok:
            logger.error("Schema still out of date after auto-migration")
            sys.exit(1)

    if diff.extra_columns:
        logger.warning("Extra columns in database (not used by the current model):")
        for c in diff.extra_columns:
            logger.warning("  %s.%s %s", c.table, c.name, c.type_sql)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
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

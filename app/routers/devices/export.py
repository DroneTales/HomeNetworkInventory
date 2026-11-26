# Home Network Inventory
# Devices UI: XLSX/CSV export.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from urllib.parse import quote
from fastapi import Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.export import to_csv_zip, to_xlsx
from app.core.deps import require_site, require_user
from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.routers.devices.base import _slug
from app.routers.devices.base import router

@router.get("/export.xlsx")
def export_devices_xlsx(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    lang = user.language
    def t(key, *args):
        from app.core.i18n import translate
        s = translate(key, lang)
        return s.format(*args) if args else s
    body = to_xlsx(db, site.id, t)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"home_network_{_slug(site.name)}_{ts}.xlsx"
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )

@router.get("/export.zip")
def export_devices_csv(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    lang = user.language
    def t(key, *args):
        from app.core.i18n import translate
        s = translate(key, lang)
        return s.format(*args) if args else s
    body = to_csv_zip(db, site.id, t, site.name)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"home_network_{_slug(site.name)}_{ts}.zip"
    return Response(
        content=body,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )

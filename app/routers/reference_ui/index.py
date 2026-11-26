# Home Network Inventory
# Reference CRUD UI: index page.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from app.core.deps import require_edit, require_site
from app.core.templating import render
from app.models.site import Site
from app.models.user import User
from app.routers.reference_ui.base import router

@router.get("", response_class=HTMLResponse)
def reference_index(
    request: Request,
    user: User = Depends(require_edit),
    site: Site = Depends(require_site),
):
    return render(
        request,
        "reference/index.html",
        user=user,
        current_site=site,
    )

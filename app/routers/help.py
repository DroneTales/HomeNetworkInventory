# Home Network Inventory
# Help page router.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.core.deps import require_user
from app.core.templating import render
from app.models.user import User

router = APIRouter(prefix="/help", tags=["help"])

@router.get("", response_class=HTMLResponse)
def help_page(
    request: Request,
    user: User = Depends(require_user),
):
    return render(request, "help/index.html", user=user)

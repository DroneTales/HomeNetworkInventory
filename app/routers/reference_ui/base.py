# Home Network Inventory
# Reference CRUD UI: shared router and form helper.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter

from app.core.templating import render

router = APIRouter(prefix="/reference", tags=["reference-ui"])

def _ref_form(
    request,
    user,
    site,
    template,
    form_action,
    is_edit,
    form_data,
    error=None,
    **extra,
):
    return render(
        request,
        template,
        user=user,
        current_site=site,
        form_action=form_action,
        is_edit=is_edit,
        error=error,
        form_data=form_data,
        **extra,
    )

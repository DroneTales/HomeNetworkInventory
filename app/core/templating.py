# Home Network Inventory
# Jinja2 rendering helper with locale and theme.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.i18n import detect_language, translate
from app.models.site import Site
from app.models.user import User

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def _resolve_theme(user: User | None) -> str:
    if user is not None and user.theme in ("light", "dark"):
        return user.theme
    return "auto"

def render(
    request: Request,
    template: str,
    user: User | None = None,
    current_site: Site | None = None,
    **extra,
) -> HTMLResponse:
    if current_site is None:
        current_site = getattr(request.state, "current_site", None)

    if user is not None:
        lang = user.language
    else:
        lang = detect_language(request.headers.get("accept-language"))

    # Extra args are substituted via str.format, e.g. t('x', name)
    def _t(key, *args):
        s = translate(key, lang)
        return s.format(*args) if args else s

    context = {
        "request": request,
        "t": _t,
        "lang": lang,
        "current_user": user,
        "current_site": current_site,
        "bs_theme": _resolve_theme(user),
    }
    context.update(extra)
    return templates.TemplateResponse(template, context)

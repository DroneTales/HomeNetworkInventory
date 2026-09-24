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
    """Страница справки. Язык берётся из профиля пользователя (через render)."""
    return render(request, "help/index.html", user=user)


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.deps import get_current_site
from app.database import SessionLocal
from app.models.user import User


class CurrentSiteMiddleware(BaseHTTPMiddleware):
    """Кладёт текущий дом (Site) в request.state.current_site.

    Определяется по cookie `hni_site` и пользователю из сессии.
    Если пользователь не залогинен, дом не выбран или недоступен —
    request.state.current_site = None.
    """

    async def dispatch(self, request: Request, call_next):
        request.state.current_site = None

        user_id = None
        try:
            user_id = request.session.get("user_id")
        except (AttributeError, AssertionError):
            # Сессия ещё не инициализирована (например, для статических файлов)
            user_id = None

        if user_id is not None:
            db = SessionLocal()
            try:
                user = db.get(User, user_id)
                if user is not None and user.is_active:
                    request.state.current_site = get_current_site(request, user, db)
            finally:
                db.close()

        return await call_next(request)

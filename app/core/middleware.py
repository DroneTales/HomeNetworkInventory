from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.deps import get_current_site
from app.database import SessionLocal
from app.models.user import User

class CurrentSiteMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.current_site = None

        user_id = None
        try:
            user_id = request.session.get("user_id")
        except (AttributeError, AssertionError):
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

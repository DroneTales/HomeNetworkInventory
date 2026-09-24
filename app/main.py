from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.core.bootstrap import ensure_default_admin
from app.core.deps import get_current_site, require_user
from app.core.i18n import load_translations
from app.core.middleware import CurrentSiteMiddleware
from app.database import Base, check_database_path, engine, get_db
from app.models.user import User

# Импортируем все модели, чтобы SQLAlchemy знал о них перед create_all().
from app import models  # noqa: F401

from app.routers import auth, connections, devices, help, profile, reference, reference_ui, sites, users

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_database_path()
    Base.metadata.create_all(bind=engine)
    ensure_default_admin()
    load_translations()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# ВАЖНО: порядок добавления middleware в Starlette — обратный порядку выполнения.
# Тот, что добавлен последним, выполняется первым.
# Нам нужно, чтобы SessionMiddleware выполнилась ДО CurrentSiteMiddleware,
# потому что вторая читает request.session. Значит, добавляем CurrentSite
# первой, а Session — второй.
app.add_middleware(CurrentSiteMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="hni_session",
    same_site="lax",
    https_only=True,
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


import time

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.models.user_site import UserSite

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None

    now = int(time.time())
    last_seen = request.session.get("last_seen")

    if last_seen is None:
        request.session["last_seen"] = now
    elif now - int(last_seen) > settings.session_timeout_seconds:
        request.session.clear()
        return None
    else:
        request.session["last_seen"] = now

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        request.session.clear()
        return None

    return user

def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    return user

def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user

def require_edit(user: User = Depends(require_user)) -> User:
    if user.role == "admin" or user.can_edit:
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

def get_accessible_sites(db: Session, user: User) -> list[Site]:
    if user.role == "admin":
        return (
            db.query(Site)
            .filter(Site.is_active == True)  # noqa: E712
            .order_by(Site.name)
            .all()
        )

    return (
        db.query(Site)
        .join(UserSite, UserSite.site_id == Site.id)
        .filter(UserSite.user_id == user.id)
        .filter(Site.is_active == True)  # noqa: E712
        .order_by(Site.name)
        .all()
    )

def user_can_access_site(db: Session, user: User, site_id: int) -> bool:
    if user.role == "admin":
        return db.get(Site, site_id) is not None

    return (
        db.query(UserSite)
        .filter(UserSite.user_id == user.id, UserSite.site_id == site_id)
        .first()
        is not None
    )

def get_current_site(request: Request, user: User, db: Session) -> Site | None:
    site_id = request.cookies.get("hni_site")
    if site_id is None:
        return None

    try:
        site_id = int(site_id)
    except (TypeError, ValueError):
        return None

    site = db.get(Site, site_id)
    if site is None or not site.is_active:
        return None

    if not user_can_access_site(db, user, site_id):
        return None

    return site

def require_site(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Site:
    site = get_current_site(request, user, db)
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/sites"},
        )
    return site

def set_current_site_cookie(response, site_id: int) -> None:
    response.set_cookie(
        key="hni_site",
        value=str(site_id),
        max_age=365 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=True,
        path="/",
    )

def clear_current_site_cookie(response) -> None:
    response.delete_cookie("hni_site", path="/")

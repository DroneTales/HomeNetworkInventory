from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_site, require_user
from app.crud import credential_type as crud_cred_type
from app.crud import device_type as crud_device_type
from app.crud import location as crud_location
from app.crud import model as crud_model
from app.crud import vendor as crud_vendor
from app.database import get_db
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/locations")
def list_locations(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    items = crud_location.list_all(db, site.id)
    return [{"id": loc.id, "name": loc.name} for loc in items]


@router.get("/device-types")
def list_device_types(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    items = crud_device_type.list_all(db)
    return [
        {"id": t.id, "name": t.name, "is_active": t.is_active}
        for t in items
    ]


@router.get("/vendors")
def list_vendors(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    items = crud_vendor.list_all(db)
    return [{"id": v.id, "name": v.name} for v in items]


@router.get("/vendors/{vendor_id}/models")
def list_models_by_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    items = crud_model.list_by_vendor(db, vendor_id)
    return [{"id": m.id, "name": m.name} for m in items]


@router.get("/credential-types")
def list_credential_types(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    site: Site = Depends(require_site),
):
    items = crud_cred_type.list_all(db)
    return [{"id": t.id, "name": t.name} for t in items]


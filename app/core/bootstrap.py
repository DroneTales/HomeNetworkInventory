# Home Network Inventory
# First-run defaults (default Admin user).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.orm import Session

from app.core.constants import ROLE_ADMIN
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User


def ensure_default_admin() -> None:
    db: Session = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return

        admin = User(
            username="Admin",
            password_hash=hash_password("Admin"),
            role=ROLE_ADMIN,
            can_edit=True,
            can_view_passwords=True,
            can_change_passwords=True,
            must_change_password=True,
            is_active=True,
            language="en",
            theme="auto",
        )
        db.add(admin)
        db.commit()
        print("[bootstrap] Default admin user created: Admin / Admin")
    finally:
        db.close()

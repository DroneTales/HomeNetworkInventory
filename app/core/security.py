# Home Network Inventory
# Password hashing and verification (bcrypt).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from passlib.hash import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.verify(plain, hashed)
    except ValueError:
        return False

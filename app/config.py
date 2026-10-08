# Home Network Inventory
# Application settings (session, database, security).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"

def _read_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"

class Settings:
    app_name = "Home Network Inventory"
    app_version = _read_version()
    app_host = "127.0.0.1"
    app_port = 8420
    database_url = "sqlite:///./home_network.db"
    session_secret = "CHANGE_ME_GENERATE_A_RANDOM_SECRET_KEY"

    session_timeout_seconds = 2 * 60 * 60

settings = Settings()

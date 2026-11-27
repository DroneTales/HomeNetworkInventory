# Home Network Inventory
# Application settings (session, database, security).
#
# Resolution order for every value: environment variable -> data/settings.json
# -> built-in default. Nothing secret is stored in this file, so the same
# config works for a GitHub clone, the end-user ZIP and the server deploy.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VERSION_FILE = BASE_DIR / "VERSION"
SETTINGS_FILE = DATA_DIR / "settings.json"


def _read_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def _load_local_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_local_settings(local: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            json.dumps(local, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.chmod(SETTINGS_FILE, 0o600)
    except OSError:
        pass


def _resolve_secret(local: dict) -> str:
    secret = os.environ.get("HNI_SESSION_SECRET") or local.get("session_secret")
    if secret:
        return secret
    secret = secrets.token_urlsafe(48)
    local["session_secret"] = secret
    _save_local_settings(local)
    return secret


class Settings:
    app_name = "Home Network Inventory"
    app_version = _read_version()

    _local = _load_local_settings()

    app_host = os.environ.get("HNI_HOST") or _local.get("host") or "127.0.0.1"
    app_port = int(os.environ.get("HNI_PORT") or _local.get("port") or 8420)
    database_url = (
        os.environ.get("HNI_DATABASE_URL")
        or _local.get("database_url")
        or f"sqlite:///{DATA_DIR / 'home_network.db'}"
    )
    session_secret = _resolve_secret(_local)
    session_timeout_seconds = 2 * 60 * 60


settings = Settings()

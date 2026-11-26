# Home Network Inventory
# Reference CRUD UI: package entry.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.routers.reference_ui.base import router  # noqa: F401
from app.routers.reference_ui import (  # noqa: F401
    credential_types,
    device_types,
    index,
    locations,
    models,
    networks,
    vendors,
)

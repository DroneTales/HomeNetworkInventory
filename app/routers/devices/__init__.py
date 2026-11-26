# Home Network Inventory
# Devices UI: package entry.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.routers.devices.base import router  # noqa: F401
from app.routers.devices import (  # noqa: F401
    export,
    form,
    list_page,
    view,
)

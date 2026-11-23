# Home Network Inventory
# MAC filter entry (per-SSID allow/deny list).
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MacFilter(Base):
    __tablename__ = "mac_filters"
    __table_args__ = (
        UniqueConstraint("wifi_network_id", "device_id", name="uq_mac_filter_wifi_device"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    wifi_network_id: Mapped[int] = mapped_column(
        ForeignKey("wifi_networks.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    wifi_network: Mapped["WiFiNetwork"] = relationship(back_populates="mac_filters")
    device: Mapped["Device"] = relationship()

# Home Network Inventory
# Wi-Fi network model.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WiFiNetwork(Base):
    __tablename__ = "wifi_networks"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    interface_id: Mapped[int] = mapped_column(
        ForeignKey("interfaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ssid: Mapped[str] = mapped_column(String(100), nullable=False)
    encryption: Mapped[str | None] = mapped_column(String(50))
    password: Mapped[str | None] = mapped_column(String(255))
    is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    device: Mapped["Device"] = relationship(back_populates="wifi_networks")
    interface: Mapped["Interface | None"] = relationship(
        back_populates="broadcast_wifi_networks",
        foreign_keys=[interface_id],
    )
    connected_interfaces: Mapped[list["Interface"]] = relationship(
        back_populates="connected_wifi_network",
        foreign_keys="Interface.connected_wifi_network_id",
    )

# Home Network Inventory
# Port forward rule model.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PortForward(Base):
    __tablename__ = "port_forwards"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_port_start: Mapped[int] = mapped_column(Integer, nullable=False)
    external_port_end: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(8), nullable=False)
    internal_device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), index=True
    )
    internal_ip_manual: Mapped[str | None] = mapped_column(String(45))
    internal_port_start: Mapped[int] = mapped_column(Integer, nullable=False)
    internal_port_end: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    device: Mapped["Device"] = relationship(
        back_populates="port_forwards",
        foreign_keys=[device_id],
    )
    internal_device: Mapped["Device | None"] = relationship(
        back_populates="port_forwards_targeted",
        foreign_keys=[internal_device_id],
        passive_deletes=True,
    )

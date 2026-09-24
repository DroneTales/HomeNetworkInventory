from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(
        ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hostname: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    human_readable_name: Mapped[str | None] = mapped_column(String(60))
    remarks: Mapped[str | None] = mapped_column(String)

    device_type_id: Mapped[int | None] = mapped_column(ForeignKey("device_types.id"))
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"))
    model_id: Mapped[int | None] = mapped_column(ForeignKey("models.id"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    network_id: Mapped[int | None] = mapped_column(ForeignKey("networks.id"))

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    site: Mapped["Site"] = relationship(back_populates="devices")
    device_type: Mapped["DeviceType | None"] = relationship(back_populates="devices")
    vendor: Mapped["Vendor | None"] = relationship(back_populates="devices")
    model: Mapped["Model | None"] = relationship(back_populates="devices")
    location: Mapped["Location | None"] = relationship(back_populates="devices")
    network: Mapped["Network | None"] = relationship(back_populates="devices")

    interfaces: Mapped[list["Interface"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    ports: Mapped[list["Port"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    wifi_networks: Mapped[list["WiFiNetwork"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    dhcp_pools: Mapped[list["DhcpPool"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    credentials: Mapped[list["Credential"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    services: Mapped[list["Service"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


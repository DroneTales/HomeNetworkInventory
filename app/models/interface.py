from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Interface(Base):
    __tablename__ = "interfaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    mac: Mapped[str | None] = mapped_column(String(17), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    connected_wifi_network_id: Mapped[int | None] = mapped_column(
        ForeignKey("wifi_networks.id", ondelete="SET NULL")
    )

    device: Mapped["Device"] = relationship(back_populates="interfaces")
    connected_wifi_network: Mapped["WiFiNetwork | None"] = relationship(
        back_populates="connected_interfaces"
    )
    ip_addresses: Mapped[list["IPAddress"]] = relationship(
        back_populates="interface", cascade="all, delete-orphan"
    )
    ports: Mapped[list["Port"]] = relationship(
        back_populates="interface", cascade="all, delete-orphan"
    )

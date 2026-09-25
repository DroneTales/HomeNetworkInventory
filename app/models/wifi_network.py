from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class WiFiNetwork(Base):
    __tablename__ = "wifi_networks"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    ssid: Mapped[str] = mapped_column(String(100), nullable=False)
    band: Mapped[str | None] = mapped_column(String(10))
    encryption: Mapped[str | None] = mapped_column(String(50))
    password: Mapped[str | None] = mapped_column(String(255))
    is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    device: Mapped["Device"] = relationship(back_populates="wifi_networks")
    connected_interfaces: Mapped[list["Interface"]] = relationship(
        back_populates="connected_wifi_network"
    )

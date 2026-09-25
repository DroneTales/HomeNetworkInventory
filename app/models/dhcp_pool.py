from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class DhcpPool(Base):
    __tablename__ = "dhcp_pools"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(100))
    start_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    end_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="dynamic")
    gateway: Mapped[str | None] = mapped_column(String(45))
    dns: Mapped[str | None] = mapped_column(String(45))
    description: Mapped[str | None] = mapped_column(String(255))

    device: Mapped["Device"] = relationship(back_populates="dhcp_pools")

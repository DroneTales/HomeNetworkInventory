from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Network(Base):
    __tablename__ = "networks"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(
        ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    network_address: Mapped[str] = mapped_column(String(45), nullable=False)
    mask: Mapped[str] = mapped_column(String(45), nullable=False)
    gateway: Mapped[str | None] = mapped_column(String(45))
    vlan: Mapped[int | None] = mapped_column()
    description: Mapped[str | None] = mapped_column(String(255))

    site: Mapped["Site"] = relationship(back_populates="networks")
    devices: Mapped[list["Device"]] = relationship(back_populates="network")
    ip_addresses: Mapped[list["IPAddress"]] = relationship(back_populates="network")

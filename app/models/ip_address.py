from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class IPAddress(Base):
    __tablename__ = "ip_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    interface_id: Mapped[int] = mapped_column(
        ForeignKey("interfaces.id", ondelete="CASCADE"), nullable=False
    )
    network_id: Mapped[int | None] = mapped_column(ForeignKey("networks.id"))

    address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    mask: Mapped[str] = mapped_column(String(45), nullable=False)
    gateway: Mapped[str | None] = mapped_column(String(45))
    dns: Mapped[str | None] = mapped_column(String(45))
    address_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    interface: Mapped["Interface"] = relationship(back_populates="ip_addresses")
    network: Mapped["Network | None"] = relationship(back_populates="ip_addresses")

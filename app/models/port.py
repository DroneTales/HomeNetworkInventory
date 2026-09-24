from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Port(Base):
    __tablename__ = "ports"
    __table_args__ = (
        UniqueConstraint("device_id", "name", name="uq_ports_device_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    interface_id: Mapped[int] = mapped_column(
        ForeignKey("interfaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    device: Mapped["Device"] = relationship(back_populates="ports")
    interface: Mapped["Interface"] = relationship(back_populates="ports")

    connections_from: Mapped[list["Connection"]] = relationship(
        back_populates="source_port",
        foreign_keys="Connection.source_port_id",
        cascade="all, delete-orphan",
    )
    connections_to: Mapped[list["Connection"]] = relationship(
        back_populates="target_port",
        foreign_keys="Connection.target_port_id",
        cascade="all, delete-orphan",
    )


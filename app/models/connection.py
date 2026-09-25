from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_port_id: Mapped[int] = mapped_column(
        ForeignKey("ports.id", ondelete="CASCADE"), nullable=False
    )
    target_port_id: Mapped[int] = mapped_column(
        ForeignKey("ports.id", ondelete="CASCADE"), nullable=False
    )
    connection_type: Mapped[str] = mapped_column(String(20), nullable=False, default="physical")
    cable_type: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source_port: Mapped["Port"] = relationship(
        back_populates="connections_from",
        foreign_keys=[source_port_id],
    )
    target_port: Mapped["Port"] = relationship(
        back_populates="connections_to",
        foreign_keys=[target_port_id],
    )

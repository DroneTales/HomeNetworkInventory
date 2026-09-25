from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    protocol: Mapped[str | None] = mapped_column(String(20))
    port: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(255))
    path: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(255))

    device: Mapped["Device"] = relationship(back_populates="services")

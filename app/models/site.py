from datetime import datetime

from sqlalchemy import Boolean, DateTime, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    photo: Mapped[bytes | None] = mapped_column(LargeBinary)
    photo_mime: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    locations: Mapped[list["Location"]] = relationship(back_populates="site")
    networks: Mapped[list["Network"]] = relationship(back_populates="site")
    devices: Mapped[list["Device"]] = relationship(back_populates="site")
    user_sites: Mapped[list["UserSite"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )


from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    models: Mapped[list["Model"]] = relationship(back_populates="vendor")
    devices: Mapped[list["Device"]] = relationship(back_populates="vendor")


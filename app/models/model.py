from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Model(Base):
    __tablename__ = "models"
    __table_args__ = (
        UniqueConstraint("vendor_id", "name", name="uq_models_vendor_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    vendor: Mapped["Vendor"] = relationship(back_populates="models")
    devices: Mapped[list["Device"]] = relationship(back_populates="model")

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    type_id: Mapped[int | None] = mapped_column(
        ForeignKey("credential_types.id", ondelete="SET NULL")
    )
    username: Mapped[str | None] = mapped_column(String(100))
    password: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(255))

    device: Mapped["Device"] = relationship(back_populates="credentials")
    type: Mapped["CredentialType | None"] = relationship(back_populates="credentials")


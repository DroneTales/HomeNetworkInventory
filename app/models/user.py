from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    can_edit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_view_passwords: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_change_passwords: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    theme: Mapped[str] = mapped_column(String(10), nullable=False, default="auto")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user_sites: Mapped[list["UserSite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

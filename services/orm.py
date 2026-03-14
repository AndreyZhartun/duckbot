from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from services.database import Base

# SQLAlchemy ORM table definition - User
# maps directly to the PostgreSQL tables
class UserORM(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    tg_username: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)

    display_name: Mapped[str] = mapped_column(Text, nullable=False)

    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="user",
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'host', 'trusted', 'admin', 'owner')", name="users_role_check"),
    )
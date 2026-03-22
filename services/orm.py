from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Text, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from services.database import Base

class UserORM(Base):
    __tablename__ = "users"
 
    id:           Mapped[uuid.UUID] = mapped_column(
                      UUID(as_uuid=True), primary_key=True,
                      server_default=func.gen_random_uuid()
                  )
    display_name: Mapped[str]            = mapped_column(Text, nullable=False)
    role:         Mapped[str]            = mapped_column(Text, nullable=False, default="user")
    telegram_id:  Mapped[Optional[int]]  = mapped_column(BigInteger, nullable=True, unique=True)
    tg_username:  Mapped[Optional[str]]  = mapped_column(Text, nullable=True, unique=True)
    created_at:   Mapped[datetime]       = mapped_column(server_default=func.now(), nullable=False)
    updated_at:   Mapped[datetime]       = mapped_column(
                      server_default=func.now(), onupdate=func.now(), nullable=False
                  )
 
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'trusted', 'host', 'admin', 'owner')",
            name="users_role_check",
        ),
    )

class EventORM(Base):
    __tablename__ = "events"
 
    id:                 Mapped[uuid.UUID]       = mapped_column(
                            UUID(as_uuid=True), primary_key=True,
                            server_default=func.gen_random_uuid()
                        )
    name:               Mapped[str]             = mapped_column(Text, nullable=False)
    description:        Mapped[str]             = mapped_column(Text, nullable=False, default="")
    host_id:            Mapped[uuid.UUID]       = mapped_column(
                            UUID(as_uuid=True),
                            ForeignKey("users.id"),
                            nullable=False
                        )
    room:               Mapped[str]             = mapped_column(Text, nullable=False)
    start_time:         Mapped[datetime]        = mapped_column(nullable=False)
    end_time:           Mapped[datetime]        = mapped_column(nullable=False)
    is_weekly_instance: Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    template_id:        Mapped[Optional[uuid.UUID]] = mapped_column(
                            UUID(as_uuid=True),
                            ForeignKey("event_templates.id", use_alter=True, name="fk_event_template"),
                            nullable=True,
                        )
    created_at:         Mapped[datetime]        = mapped_column(server_default=func.now(), nullable=False)
    updated_at:         Mapped[datetime]        = mapped_column(
                            server_default=func.now(), onupdate=func.now(), nullable=False
                        )
 
    __table_args__ = (
        CheckConstraint("room IN ('room_a', 'room_b', 'both')", name="events_room_check"),
        CheckConstraint("end_time > start_time", name="events_time_check"),
    )
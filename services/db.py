from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update

from models.models import Event, RoomChoice, User, UserRole
from services.database import get_db
from services.orm import EventORM, UserORM

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _orm_to_user(row: UserORM) -> User:
    return User(
        id           = str(row.id),
        display_name = row.display_name,
        role         = UserRole(row.role),
        telegram_id  = row.telegram_id,
        tg_username  = row.tg_username,
        created_at   = row.created_at,
        updated_at   = row.updated_at,
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_or_create_user(
    telegram_id: int,
    full_name: str,
    tg_username: Optional[str] = None,
) -> User:
    """
    Called on every user interaction. Lookup priority:
      1. Match by telegram_id
      2. Match by tg_username (picks up pre-seeded rows)
      3. Create new row

    Always syncs telegram_id and tg_username on the found row so
    pre-seeded users get their real ID filled in on first /start.
    """
    async with get_db() as db:

        # 1. Match by telegram_id
        result = await db.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        row = result.scalar_one_or_none()

        if row:
            changed = {}
            # sync tg username if changed
            if row.tg_username != tg_username:
                changed["tg_username"] = tg_username
            if changed:
                await db.execute(
                    update(UserORM).where(UserORM.id == row.id).values(**changed)
                )
                await db.flush()
                await db.refresh(row)
            return _orm_to_user(row)

        # 2. Match by tg_username (pre-seeded row without a telegram_id yet)
        if tg_username:
            result = await db.execute(
                select(UserORM).where(
                    UserORM.tg_username == tg_username,
                    UserORM.telegram_id.is_(None),
                )
            )
            row = result.scalar_one_or_none()

            if row:
                # update telegram id
                await db.execute(
                    update(UserORM)
                    .where(UserORM.id == row.id)
                    .values(
                        telegram_id  = telegram_id,
                        display_name = full_name,   # replace placeholder name
                    )
                )
                await db.flush()
                await db.refresh(row)
                logger.info(f"Pre-seeded user claimed: @{tg_username} → ID {telegram_id}")
                return _orm_to_user(row)

        # 3. Brand new user
        role = UserRole.USER

        new_user = UserORM(
            display_name = full_name,
            telegram_id  = telegram_id,
            tg_username  = tg_username,
            role         = role.value,
        )
        db.add(new_user)
        await db.flush()
        await db.refresh(new_user)
        return _orm_to_user(new_user)


async def get_user(user_id: str) -> Optional[User]:
    """Fetch by internal UUID."""
    async with get_db() as db:
        result = await db.execute(
            select(UserORM).where(UserORM.id == uuid.UUID(user_id))
        )
        row = result.scalar_one_or_none()
        return _orm_to_user(row) if row else None


async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    async with get_db() as db:
        result = await db.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        row = result.scalar_one_or_none()
        return _orm_to_user(row) if row else None


async def get_user_by_username(tg_username: str) -> Optional[User]:
    """Look up by @username — strips @ if present."""
    username = tg_username.lstrip("@")
    async with get_db() as db:
        result = await db.execute(
            select(UserORM).where(UserORM.tg_username == username)
        )
        row = result.scalar_one_or_none()
        return _orm_to_user(row) if row else None


async def update_display_name(user_id: str, new_name: str) -> User:
    async with get_db() as db:
        await db.execute(
            update(UserORM)
            .where(UserORM.id == uuid.UUID(user_id))
            .values(display_name=new_name)
        )
        result = await db.execute(
            select(UserORM).where(UserORM.id == uuid.UUID(user_id))
        )
        return _orm_to_user(result.scalar_one())


async def set_user_role(user_id: str, role: UserRole) -> None:
    async with get_db() as db:
        await db.execute(
            update(UserORM)
            .where(UserORM.id == uuid.UUID(user_id))
            .values(role=role.value)
        )


async def list_users() -> list[User]:
    async with get_db() as db:
        result = await db.execute(
            select(UserORM).order_by(UserORM.display_name)
        )
        return [_orm_to_user(row) for row in result.scalars().all()]


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def _orm_to_event(row: EventORM) -> Event:
    return Event(
        id                 = str(row.id),
        name               = row.name,
        description        = row.description,
        host_id            = str(row.host_id),
        room               = RoomChoice(row.room),
        start_time         = row.start_time,
        end_time           = row.end_time,
        is_weekly_instance = row.is_weekly_instance,
        template_id        = str(row.template_id) if row.template_id else None,
    )


async def create_event(
    name:               str,
    description:        str,
    host_id:            str,
    room:               RoomChoice,
    start_time:         datetime,
    end_time:           datetime,
    is_weekly_instance: bool = False,
    template_id:        Optional[str] = None,
) -> Event:
    async with get_db() as db:
        row = EventORM(
            name               = name,
            description        = description,
            host_id            = uuid.UUID(host_id),
            room               = room.value,
            start_time         = start_time,
            end_time           = end_time,
            is_weekly_instance = is_weekly_instance,
            template_id        = uuid.UUID(template_id) if template_id else None,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _orm_to_event(row)


async def get_event(event_id: str) -> Optional[Event]:
    async with get_db() as db:
        result = await db.execute(
            select(EventORM).where(EventORM.id == uuid.UUID(event_id))
        )
        row = result.scalar_one_or_none()
        return _orm_to_event(row) if row else None


async def list_events_in_range(start: datetime, end: datetime) -> list[Event]:
    async with get_db() as db:
        result = await db.execute(
            select(EventORM)
            .where(EventORM.start_time >= start)
            .where(EventORM.start_time <= end)
            .order_by(EventORM.start_time)
        )
        return [_orm_to_event(row) for row in result.scalars().all()]


async def list_events_from(after: datetime) -> list[Event]:
    async with get_db() as db:
        result = await db.execute(
            select(EventORM)
            .where(EventORM.start_time >= after)
            .order_by(EventORM.start_time)
        )
        return [_orm_to_event(row) for row in result.scalars().all()]


async def delete_event(event_id: str) -> None:
    async with get_db() as db:
        row = await db.get(EventORM, uuid.UUID(event_id))
        if row:
            await db.delete(row)
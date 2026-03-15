from __future__ import annotations

import logging
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
        telegram_id=row.telegram_id,
        display_name=row.display_name,
        tg_username=row.tg_username,
        role=UserRole(row.role),
        created_at=row.created_at,
        updated_at=row.updated_at,
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
    Fetches the user if they exist, otherwise creates them with default role.
    Always syncs tg_username with the latest value from Telegram.
    full_name is only used on first insert as the default display_name.
    """
    async with get_db() as db:
        result = await db.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )

        row = result.scalar_one_or_none()

        if row:
            # Sync username if it changed or was missing
            if row.tg_username != tg_username:
                await db.execute(
                    update(UserORM)
                    .where(UserORM.telegram_id == telegram_id)
                    .values(tg_username=tg_username)
                )
                await db.flush()
                await db.refresh(row)
            return _orm_to_user(row)

        # First time — USER role
        role = UserRole.USER

        new_user = UserORM(
            telegram_id=telegram_id,
            display_name=full_name,
            tg_username=tg_username,
            role=role.value,
        )

        db.add(new_user)
        await db.flush()
        await db.refresh(new_user)
        return _orm_to_user(new_user)


async def get_user_by_username(tg_username: str) -> Optional[User]:
    """Look up a user by their Telegram @username (strip @ if present)."""
    username = tg_username.lstrip("@")
    async with get_db() as db:
        result = await db.execute(
            select(UserORM).where(UserORM.tg_username == username)
        )

        row = result.scalar_one_or_none()
        return _orm_to_user(row) if row else None


async def get_user(telegram_id: int) -> Optional[User]:
    async with get_db() as db:
        result = await db.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        row = result.scalar_one_or_none()
        return _orm_to_user(row) if row else None


async def update_display_name(telegram_id: int, new_name: str) -> User:
    async with get_db() as db:
        await db.execute(
            update(UserORM)
            .where(UserORM.telegram_id == telegram_id)
            .values(display_name=new_name)
        )
        result = await db.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        row = result.scalar_one()
        return _orm_to_user(row)


async def set_user_role(telegram_id: int, role: UserRole) -> None:
    async with get_db() as db:
        await db.execute(
            update(UserORM)
            .where(UserORM.telegram_id == telegram_id)
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
        id=str(row.id),
        name=row.name,
        description=row.description,
        host_id=row.host_id,
        room=RoomChoice(row.room),
        start_time=row.start_time,
        end_time=row.end_time,
        is_weekly_instance=row.is_weekly_instance,
        template_id=str(row.template_id) if row.template_id else None,
    )
 
 
async def create_event(
    name: str,
    description: str,
    host_id: int,
    room: RoomChoice,
    start_time: datetime,
    end_time: datetime,
    is_weekly_instance: bool = False,
    template_id: Optional[str] = None,
) -> Event:
    async with get_db() as db:
        row = EventORM(
            name=name,
            description=description,
            host_id=host_id,
            room=room.value,
            start_time=start_time,
            end_time=end_time,
            is_weekly_instance=is_weekly_instance,
            template_id=template_id,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _orm_to_event(row)
 
 
async def get_event(event_id: str) -> Optional[Event]:
    import uuid
    async with get_db() as db:
        result = await db.execute(
            select(EventORM).where(EventORM.id == uuid.UUID(event_id))
        )
        row = result.scalar_one_or_none()
        return _orm_to_event(row) if row else None
 
 
async def list_events_in_range(start: datetime, end: datetime) -> list[Event]:
    """All events whose start_time falls within [start, end]."""
    async with get_db() as db:
        result = await db.execute(
            select(EventORM)
            .where(EventORM.start_time >= start)
            .where(EventORM.start_time <= end)
            .order_by(EventORM.start_time)
        )
        return [_orm_to_event(row) for row in result.scalars().all()]
 
 
async def list_events_from(after: datetime) -> list[Event]:
    """All events starting after the given datetime, ordered by start_time."""
    async with get_db() as db:
        result = await db.execute(
            select(EventORM)
            .where(EventORM.start_time >= after)
            .order_by(EventORM.start_time)
        )
        return [_orm_to_event(row) for row in result.scalars().all()]
 
 
async def delete_event(event_id: str) -> None:
    import uuid
    async with get_db() as db:
        row = await db.get(EventORM, uuid.UUID(event_id))
        if row:
            await db.delete(row)
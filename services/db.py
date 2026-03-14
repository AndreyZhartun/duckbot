from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, update

from models.models import User, UserRole
from services.database import get_db
from services.orm import UserORM

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
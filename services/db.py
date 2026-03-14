"""
services/db.py
All database queries. Uses SQLAlchemy async ORM — all queries are
parameterised automatically, preventing SQL injection.

This file currently covers the users table only.
Events, signups and templates will be added in subsequent steps.
"""

from __future__ import annotations

import logging
import os
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
        role=UserRole(row.role),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_or_create_user(telegram_id: int, full_name: str) -> tuple[User, bool]:
    """
    Fetches the user if they exist, otherwise creates them with default role.
    Returns (user, created) where created=True means it's their first time.

    full_name is only used on first insert as the default display_name.
    After that the stored display_name is always used.
    Users can customise display_name in the bot.
    """
    async with get_db() as db:
        result = await db.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        row = result.scalar_one_or_none()

        # found an existing user
        if row:
            return _orm_to_user(row), False

        # First time — role as USER
        # owner_id = int(os.environ.get("OWNER_TELEGRAM_ID", "0"))
        # role = UserRole.OWNER if telegram_id == owner_id else UserRole.USER
        role = UserRole.USER

        new_user = UserORM(
            telegram_id=telegram_id,
            display_name=full_name,
            role=role.value,
        )

        db.add(new_user)

        await db.flush()   # get DB-generated timestamps before commit
        await db.refresh(new_user)
        return _orm_to_user(new_user), True


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
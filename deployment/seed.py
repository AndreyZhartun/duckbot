"""
seed.py
Populates the database with the owner and pre-configured admins.
Run after init.sql on every deploy.

Required environment variables:
  OWNER_TELEGRAM_ID  — numeric Telegram ID of the bot owner
  SEED_ADMINS        — comma-separated @usernames to pre-seed as admins
                       e.g. "alice,bob"  (can be empty or omitted)

Owner display name is set to 'owner' and can be changed via /profile.
Admin display names are set to their username and overwritten on first /start.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def run() -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from services.database import close_engine, get_db
    from services.orm import UserORM

    owner_id_str = os.environ.get("OWNER_TELEGRAM_ID")
    admins_str   = os.environ.get("SEED_ADMINS", "")

    if not owner_id_str:
        logger.error("OWNER_TELEGRAM_ID must be set.")
        sys.exit(1)

    owner_id = int(owner_id_str)
    admin_usernames = [
        u.strip().lstrip("@")
        for u in admins_str.split(",")
        if u.strip()
    ]

    async with get_db() as db:

        # --- Owner ---
        stmt = (
            pg_insert(UserORM)
            .values(
                display_name = "AZ",
                telegram_id  = owner_id,
                tg_username  = None,
                role         = "owner",
            )
            .on_conflict_do_update(
                index_elements=["telegram_id"],
                set_={"role": "owner"},   # preserve display_name if already personalised
            )
        )
        await db.execute(stmt)
        logger.info(f"Owner upserted: telegram_id")

        # --- Admins ---
        # No telegram_id yet — filled in automatically on first /start
        # display_name is set to username as placeholder, overwritten on first /start
        for username in admin_usernames:
            stmt = (
                pg_insert(UserORM)
                .values(
                    display_name = username,
                    tg_username  = username,
                    telegram_id  = None,
                    role         = "admin",
                )
                .on_conflict_do_update(
                    index_elements=["tg_username"],
                    set_={"role": "admin"},   # preserve display_name if already claimed
                )
            )
            await db.execute(stmt)
            logger.info(f"Admin upserted")

    await close_engine()
    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(run())
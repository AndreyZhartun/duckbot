"""
handlers/utils.py
Shared decorators, guards, and formatting helpers used across all handlers.
"""

from __future__ import annotations

import functools
import logging
from datetime import datetime
from html import escape
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from models.models import Event, RoomChoice, User, UserRole
from services import db

logger = logging.getLogger(__name__)

ROOM_LABELS = {
    RoomChoice.ROOM_A: "🟦 Room A",
    RoomChoice.ROOM_B: "🟩 Room B",
    RoomChoice.BOTH: "🟪 Both Rooms",
}

WEEKDAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ---------------------------------------------------------------------------
# HTML escaping
# ---------------------------------------------------------------------------

def escape_user(user: User) -> User:
    """
    Returns a copy of the User with all string fields HTML-escaped.
    Use this before inserting any user data into HTML-parsed messages
    to prevent injection via display names or usernames.

    Usage:
        safe = escape_user(user)
        await update.message.reply_text(
            f"Hello, <b>{safe.display_name}</b>",
            parse_mode=ParseMode.HTML,
        )
    """
    from dataclasses import replace
    return replace(
        user,
        display_name=escape(user.display_name),
        tg_username=escape(user.tg_username) if user.tg_username else None,
    )


# ---------------------------------------------------------------------------
# Role guard decorator
# ---------------------------------------------------------------------------

def require_role(*roles: UserRole):
    """
    Decorator that injects the current `User` object into the handler and
    rejects the request if the user's role is insufficient.

    Usage:
        @require_role(UserRole.HOST, UserRole.ADMIN, UserRole.OWNER)
        async def my_handler(update, context, user: User):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            tg_user = update.effective_user
            user = await db.get_or_create_user(
                telegram_id=tg_user.id,
                full_name=tg_user.full_name,
                tg_username=tg_user.username,
            )
            if user.role not in roles:
                await update.effective_message.reply_text(
                    "⛔ You don't have permission to do that."
                )
                return
            return await func(update, context, user, *args, **kwargs)
        return wrapper
    return decorator


def require_any_role(func: Callable):
    """
    Lighter guard — just ensures the user exists in the DB.
    Useful for handlers open to all registered users.
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        tg_user = update.effective_user
        user = await db.get_or_create_user(
            telegram_id=tg_user.id,
            full_name=tg_user.full_name,
            tg_username=tg_user.username,
        )
        return await func(update, context, user, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_event_summary(event: Event, signup_count: int = 0) -> str:
    room_label = ROOM_LABELS.get(event.room, event.room.value)
    start = event.start_time.strftime("%a %d %b, %H:%M")
    end = event.end_time.strftime("%H:%M")
    weekly_tag = " 🔁" if event.is_weekly_instance else ""
    return (
        f"*{event.name}*{weekly_tag}\n"
        f"📅 {start} – {end}\n"
        f"📍 {room_label}\n"
        f"👥 {signup_count}/{event.max_people} (min: {event.min_people})\n"
        f"_{event.description}_"
    )


def format_event_detail(event: Event, signups: list, current_user_id: int) -> str:
    room_label = ROOM_LABELS.get(event.room, event.room.value)
    start = event.start_time.strftime("%A %d %B %Y, %H:%M")
    end = event.end_time.strftime("%H:%M")
    signed_up = any(s.user_id == current_user_id for s in signups)
    signup_status = "✅ You are signed up" if signed_up else "❌ Not signed up"
    weekly_tag = "\n🔁 _Weekly recurring event_" if event.is_weekly_instance else ""

    return (
        f"*{event.name}*{weekly_tag}\n\n"
        f"{event.description}\n\n"
        f"📅 {start} – {end}\n"
        f"📍 {room_label}\n"
        f"👥 {len(signups)}/{event.max_people} people (min: {event.min_people})\n\n"
        f"{signup_status}"
    )


def parse_date_input(text: str) -> date | None:
    """Parses DD/MM/YYYY or DD.MM.YYYY into a date object."""
    from datetime import date as date_type
    for fmt in ("%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_time_range(
    text: str,
    day: "date",
) -> tuple["datetime", "datetime", str | None] | None:
    """
    Parses 'HH:MM HH:MM' into (start_datetime, end_datetime, error).
    Returns None if the format is completely unparseable.
    Returns (start, end, error_message) if parsed but invalid.
    Returns (start, end, None) if valid.

    Constraints:
      - Start and end must be within 07:00–22:00
      - End must be after start
    """
    from datetime import datetime as dt, date as date_type, time
    parts = text.strip().split()
    if len(parts) != 2:
        return None

    def _parse_t(s: str) -> time | None:
        try:
            h, m = s.split(":")
            return time(int(h), int(m))
        except (ValueError, TypeError):
            return None

    start_t = _parse_t(parts[0])
    end_t   = _parse_t(parts[1])

    if not start_t or not end_t:
        return None

    start_dt = dt.combine(day, start_t)
    end_dt   = dt.combine(day, end_t)

    if start_t.hour < 7 or start_t.hour >= 22:
        return start_dt, end_dt, "Start time must be between 07:00 and 22:00."
    if end_t.hour < 7 or end_t > time(22, 0):
        return start_dt, end_dt, "End time must be between 07:00 and 22:00."
    if end_dt <= start_dt:
        return start_dt, end_dt, "End time must be after start time."

    return start_dt, end_dt, None
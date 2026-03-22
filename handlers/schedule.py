"""
handlers/schedule.py
Schedule display for all users.

  /schedule (or menu button) — full week view for the current Mon–Sun
  /upcoming                  — simple chronological list of all future events
                               beyond the current week
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from html import escape

from babel.dates import format_date, format_datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from handlers.utils import ROOM_LABELS, require_any_role
from models.models import Event, RoomChoice, User
from services import db

logger = logging.getLogger(__name__)

SCHEDULE_START_HOUR = 7
SCHEDULE_END_HOUR   = 22
LOCALE              = "ru_RU"

ROOM_ORDER = [RoomChoice.ROOM_A, RoomChoice.ROOM_B]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _week_bounds() -> tuple[date, date]:
    """Returns Monday and Sunday of the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _fmt_day_header(day: date) -> str:
    """
    e.g. "21 марта - суббота"
    format_date with 'd MMMM' gives genitive month (марта, апреля…)
    'EEEE' gives full weekday name in Russian.
    """
    date_part = format_date(day, format="d MMMM", locale=LOCALE)
    weekday   = format_date(day, format="EEEE",   locale=LOCALE)
    return f"{date_part} - {weekday}"


def _fmt_short_date(day: date) -> str:
    """e.g. "21 мар" — for the week label header."""
    return format_date(day, format="d MMM", locale=LOCALE)


def _format_day_schedule(day: date, events: list[Event]) -> str:
    lines = [f"<b>{_fmt_day_header(day)}</b>"]

    for room in ROOM_ORDER:
        room_label = ROOM_LABELS.get(room, room.value)
        lines.append(f"\n{room_label}")

        room_events = sorted(
            [e for e in events if e.room in (room, RoomChoice.BOTH)],
            key=lambda e: e.start_time,
        )

        cursor       = SCHEDULE_START_HOUR * 60
        end_boundary = SCHEDULE_END_HOUR   * 60

        for event in room_events:
            event_start = event.start_time.hour * 60 + event.start_time.minute
            event_end   = event.end_time.hour   * 60 + event.end_time.minute

            if cursor < event_start:
                lines.append(_free_slot(cursor, event_start))

            start_str = _fmt_time(event_start)
            end_str   = _fmt_time(event_end)
            desc_line = f"\n{escape(event.description)}" if event.description else ""
            lines.append(
                f"{start_str} - {end_str} — <b>{escape(event.name)}</b>{desc_line}"
            )
            cursor = max(cursor, event_end)

        if cursor < end_boundary:
            lines.append(_free_slot(cursor, end_boundary))

    return "\n".join(lines)


def _free_slot(start_min: int, end_min: int) -> str:
    return f"{_fmt_time(start_min)} - {_fmt_time(end_min)} — свободно"


def _fmt_time(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h}:{m:02d}"


# ---------------------------------------------------------------------------
# /schedule — current week, full day-by-day view
# ---------------------------------------------------------------------------

@require_any_role
async def cmd_schedule(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    monday, sunday = _week_bounds()

    # Fetch all events for the week in one query
    events = await db.list_events_in_range(
        start=datetime.combine(monday, datetime.min.time()),
        end=datetime.combine(sunday, datetime.max.time()),
    )

    # Group by date
    by_day: dict[date, list[Event]] = {
        monday + timedelta(days=i): [] for i in range(7)
    }
    for event in events:
        day = event.start_time.date()
        if day in by_day:
            by_day[day].append(event)

    blocks = [_format_day_schedule(day, day_events) for day, day_events in by_day.items()]
    full_schedule = "\n\n".join(blocks)

    week_label = f"{_fmt_short_date(monday)} – {_fmt_short_date(sunday)} {sunday.year}"
    await update.effective_message.reply_text(
        f"📅 <b>Расписание {week_label}</b>\n\n{full_schedule}",
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# /upcoming — simple list of events after the current week
# ---------------------------------------------------------------------------

@require_any_role
async def cmd_upcoming(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    _, sunday = _week_bounds()
    after = datetime.combine(sunday + timedelta(days=1), datetime.min.time())

    events = await db.list_events_from(after)

    if not events:
        await update.effective_message.reply_text("Нет предстоящих событий после этой недели.")
        return

    lines = ["<b>Предстоящие события (после этой недели)</b>\n"]
    for event in events:
        room_label = ROOM_LABELS.get(event.room, event.room.value)
        date_str   = format_date(event.start_time.date(), format="d MMMM yyyy", locale=LOCALE)
        time_str   = f"{event.start_time.strftime('%H:%M')} – {event.end_time.strftime('%H:%M')}"
        desc_line  = f"\n  {escape(event.description)}" if event.description else ""
        lines.append(
            f"📅 <b>{date_str}</b>, {time_str}\n"
            f"  <b>{escape(event.name)}</b> — {room_label}{desc_line}"
        )

    await update.effective_message.reply_text(
        "\n\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

def register(app) -> None:
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("upcoming", cmd_upcoming))
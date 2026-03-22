"""
handlers/host.py
Event creation and management for hosts and above.

Future compatibility notes:
  - co_host_ids column can be added to events table; ownership checks
    should use an is_event_manager(user, event) helper (stub below)
  - template_id foreign key is already in the DB schema; when templates
    are implemented, creation flow can pre-fill fields from the template
    and skip steps where values are already set
"""

from __future__ import annotations

import logging
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from handlers.utils import ROOM_LABELS, escape_user, require_role
from models.models import RoomChoice, User, UserRole
from services import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

HOST_AND_ABOVE = (UserRole.HOST, UserRole.ADMIN, UserRole.OWNER)

# ---------------------------------------------------------------------------
# Conversation states
# ---------------------------------------------------------------------------

(
    CREATE_NAME,
    CREATE_DESC,
    CREATE_ROOM,
    CREATE_DAY,
    CREATE_START,
    CREATE_END,
) = range(6)

# Callback prefixes
CB_ROOM   = "hcr"   # host create room
CB_SKIP   = "hcs"   # host create skip (description)


# ---------------------------------------------------------------------------
# Ownership helper — stub for future co-host support
# ---------------------------------------------------------------------------

def is_event_manager(user: User, event) -> bool:
    """
    Returns True if the user has management rights over the event.
    Currently only the host and admins/owners qualify.
    When co-hosts are added, extend this to check event.co_host_ids.
    """
    if user.role in (UserRole.ADMIN, UserRole.OWNER):
        return True
    return event.host_id == user.telegram_id


# ---------------------------------------------------------------------------
# /create_event — ConversationHandler
# ---------------------------------------------------------------------------

@require_role(*HOST_AND_ABOVE)
async def cmd_create_event(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> int:
    context.user_data.clear()
    context.user_data["host_id"] = user.id   # internal UUID

    # template_id hook: if context.user_data.get("template_id") is set by
    # a future template flow, pre-fill fields and skip those steps here.

    await update.effective_message.reply_text(
        "🎉 <b>Новое событие</b> — Шаг 1/5\n\nВведите название",
        parse_mode=ParseMode.HTML,
    )
    return CREATE_NAME


async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Skip", callback_data=CB_SKIP)
    ]])
    await update.message.reply_text(
        "Шаг 2/5 — Описание? (опционально)",
        reply_markup=keyboard,
    )
    return CREATE_DESC


async def received_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["description"] = update.message.text.strip()
    return await _ask_room(update.message)


async def skipped_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["description"] = ""
    return await _ask_room(query.message)


async def _ask_room(message) -> int:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"{CB_ROOM}:{room.value}")]
        for room, label in ROOM_LABELS.items()
    ])
    await message.reply_text("Шаг 3/5 — Какая комната?", reply_markup=keyboard)
    return CREATE_ROOM


async def received_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["room"] = RoomChoice(query.data.split(":")[1])
    await query.message.reply_text(
        "Шаг 4/5 — Какой день?\nФормат: <code>дд.мм.гггг</code>",
        parse_mode=ParseMode.HTML,
    )
    return CREATE_DAY


async def received_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from handlers.utils import parse_date_input
    day = parse_date_input(update.message.text)
    if not day:
        await update.message.reply_text(
            "❌ Couldn't parse that. Use <code>DD/MM/YYYY</code> or <code>DD.MM.YYYY</code>",
            parse_mode=ParseMode.HTML,
        )
        return CREATE_DAY

    context.user_data["day"] = day
    await update.message.reply_text(
        "Шаг 5/5 — Время начала и конца?\n"
        "Формат: два времени через пробел (<code>HH:MM HH:MM</code>), например <code>14:00 17:00</code>\n"
        "Доступное время: 07:00 – 22:00",
        parse_mode=ParseMode.HTML,
    )
    return CREATE_START


async def received_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from handlers.utils import parse_time_range
    text = update.message.text.strip()
    result = parse_time_range(text, context.user_data["day"])

    if result is None:
        await update.message.reply_text(
            "❌ Couldn't parse. Use <code>HH:MM HH:MM</code> e.g. <code>14:00 17:00</code>",
            parse_mode=ParseMode.HTML,
        )
        return CREATE_START

    start_time, end_time, error = result
    if error:
        await update.message.reply_text(f"❌ {escape(error)}", parse_mode=ParseMode.HTML)
        return CREATE_START

    data = context.user_data
    event = await db.create_event(
        name=data["name"],
        description=data["description"],
        host_id=data["host_id"],
        room=data["room"],
        start_time=start_time,
        end_time=end_time,
    )

    room_label = ROOM_LABELS.get(event.room, event.room.value)
    desc_line = f"\n{escape(event.description)}" if event.description else ""
    await update.message.reply_text(
        f"✅ <b>Событие создано!</b>\n\n"
        f"<b>{escape(event.name)}</b>{desc_line}\n"
        f"📅 {event.start_time.strftime('%d %b %Y, %H:%M')} – {event.end_time.strftime('%H:%M')}\n"
        f"📍 {room_label}",
        parse_mode=ParseMode.HTML,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("❌ Создание события отменено")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

def register(app) -> None:
    create_conv = ConversationHandler(
        entry_points=[CommandHandler("create_event", cmd_create_event)],
        states={
            CREATE_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
            CREATE_DESC:  [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_desc),
                CallbackQueryHandler(skipped_desc, pattern=f"^{CB_SKIP}$"),
            ],
            CREATE_ROOM:  [CallbackQueryHandler(received_room, pattern=f"^{CB_ROOM}:")],
            CREATE_DAY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, received_day)],
            CREATE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_times)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True,
    )

    app.add_handler(create_conv)
"""
Handles user identity and the /start greeting:
  /start   — personalised greeting with role-aware inline buttons
  /profile — show current profile with option to change display name
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

from models.models import User, UserRole
from services import db
from constants import BOT_VERSION

from utils.validation import MIN_NAME_LENGTH, MAX_NAME_LENGTH
from utils.messages import COMMAND_END_MESSAGE_FOOTER

logger = logging.getLogger(__name__)

# Conversation state
WAITING_FOR_NAME = 0

CB_CHANGE_NAME = "profile_change_name"
CB_CANCEL_NAME = "profile_cancel_name"


# ---------------------------------------------------------------------------
# Role-aware keyboard builder
# ---------------------------------------------------------------------------

def _build_menu(role: UserRole) -> InlineKeyboardMarkup:
    """
    Returns an inline keyboard showing only the actions available to this role.
    Buttons are grouped into rows of 2 for readability.
    """
    user_buttons = [
        # InlineKeyboardButton("📅 Events", switch_inline_query_current_chat="/events"),
        # InlineKeyboardButton("🎟 My Signups", switch_inline_query_current_chat="/myevents"),
        InlineKeyboardButton("👤 Мой профиль", switch_inline_query_current_chat="/profile"),
    ]

    host_buttons = [
        InlineKeyboardButton("➕ Create Event", switch_inline_query_current_chat="/create_event"),
        InlineKeyboardButton("🎪 My Events", switch_inline_query_current_chat="/my_hosted"),
        InlineKeyboardButton("🔁 Create Template", switch_inline_query_current_chat="/create_template"),
        InlineKeyboardButton("📋 My Templates", switch_inline_query_current_chat="/my_templates"),
    ]

    admin_buttons = [
        InlineKeyboardButton("👥 All Users", switch_inline_query_current_chat="/users"),
        InlineKeyboardButton("🗂 All Events", switch_inline_query_current_chat="/all_events"),
    ]

    all_buttons = user_buttons[:]

    # if role in (UserRole.HOST, UserRole.ADMIN, UserRole.OWNER):
    #     all_buttons += host_buttons

    # if role in (UserRole.ADMIN, UserRole.OWNER):
    #     all_buttons += admin_buttons

    rows = [all_buttons[i:i + 2] for i in range(0, len(all_buttons), 2)]
    return InlineKeyboardMarkup(rows)


def _role_label(role: UserRole) -> str:
    return {
        UserRole.USER: "👤 Посетитель",
        UserRole.TRUSTED: "⭐ Доверенный",
        UserRole.HOST: "🎲 Организатор",
        UserRole.ADMIN: "⚔️ Администратор",
        UserRole.OWNER: "🔧 Создатель",
    }.get(role, role.value)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = await db.get_or_create_user(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        tg_username=tg_user.username,
    )

    await update.message.reply_text(
        # TODO make an util fn that escapes the user object fully
        f"<b>Привет, {escape(user.display_name)}!</b>\n\n"
        f"Это УткоБот 🐸 (версия {BOT_VERSION})\n\n"
        f"Ваша роль: {_role_label(user.role)}\n\n"
        f"Доступные команды:",
        parse_mode=ParseMode.HTML,
        reply_markup=_build_menu(user.role),
    )


# ---------------------------------------------------------------------------
# /profile
# ---------------------------------------------------------------------------

async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = await db.get_or_create_user(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        tg_username=tg_user.username,
    )

    member_since = (
        user.created_at.strftime("%d %b %Y")
        if user.created_at else "—"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✏️ Поменять имя", callback_data=CB_CHANGE_NAME)
    ]])

    await update.message.reply_text(
        f"<b>Ваш Профиль</b>\n\n"
        f"Отображаемое имя: <b>{escape(user.display_name)}</b>\n"
        f"Роль: {_role_label(user.role)}\n"
        f"Создан: {member_since}",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# Change display name — inline button → ConversationHandler
# ---------------------------------------------------------------------------

async def cb_change_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"Введите новое имя (от {MIN_NAME_LENGTH} до {MAX_NAME_LENGTH} символов).\n\n"
        "/cancel - оставить текущее имя",
    )
    return WAITING_FOR_NAME


async def received_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()

    if len(new_name) < 2:
        await update.message.reply_text(f"Имя должно быть не меньше {MIN_NAME_LENGTH} символов. Введите имя еще раз:")
        return WAITING_FOR_NAME

    if len(new_name) > 64:
        await update.message.reply_text(f"Имя должно быть не больше {MAX_NAME_LENGTH} символов. Введите имя еще раз:")
        return WAITING_FOR_NAME

    user = await db.update_display_name(update.effective_user.id, new_name)
    await update.message.reply_text(
        f"Имя изменено на: <b>{escape(user.display_name)}</b>\n{COMMAND_END_MESSAGE_FOOTER}",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def cancel_name_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"Изменение имени отменено\n{COMMAND_END_MESSAGE_FOOTER}"
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

def register(app) -> None:
    name_change_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_change_name, pattern=f"^{CB_CHANGE_NAME}$")],
        states={
            WAITING_FOR_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_new_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_name_change)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(name_change_conv)
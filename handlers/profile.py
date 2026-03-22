from __future__ import annotations

import logging

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

from utils.parsing import escape_user
from models.models import User, UserRole
from services import db
from constants import BOT_VERSION

from utils.validation import MIN_NAME_LENGTH, MAX_NAME_LENGTH
from utils.messages import COMMAND_END_MESSAGE_FOOTER

logger = logging.getLogger(__name__)

# Conversation state
WAITING_FOR_NAME = 0

CB_CHANGE_NAME = "profile_change_name"


# Callback data for menu buttons
CB_MENU_SCHEDULE      = "menu_schedule"
CB_MENU_UPCOMING      = "menu_upcoming"
CB_MENU_PROFILE       = "menu_profile"
CB_MENU_CREATE_EVENT  = "menu_create_event"
CB_MENU_USERS         = "menu_users"
CB_MENU_ALL_EVENTS    = "menu_all_events"


# ---------------------------------------------------------------------------
# Role-aware keyboard builder
# ---------------------------------------------------------------------------

def _build_menu(role: UserRole) -> InlineKeyboardMarkup:
    user_buttons = [
        InlineKeyboardButton("📅 Расписание", callback_data=CB_MENU_SCHEDULE),
        InlineKeyboardButton("🔜 События после текущей недели", callback_data=CB_MENU_UPCOMING),
        InlineKeyboardButton("👤 Мой профиль", callback_data=CB_MENU_PROFILE),
    ]

    host_buttons = [
        InlineKeyboardButton("➕ Создать событие", callback_data="hce"),
    ]

    admin_buttons = [
        # InlineKeyboardButton("👥 Все пользователи", callback_data=CB_MENU_USERS),
        # InlineKeyboardButton("💫 Все события", callback_data=CB_MENU_ALL_EVENTS),
    ]

    all_buttons = user_buttons[:]

    if role in (UserRole.HOST, UserRole.ADMIN, UserRole.OWNER):
        all_buttons += host_buttons

    # if role in (UserRole.ADMIN, UserRole.OWNER):
    #     all_buttons += admin_buttons

    rows = [all_buttons[i:i + 2] for i in range(0, len(all_buttons), 2)]
    return InlineKeyboardMarkup(rows)


async def cb_menu_dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from handlers import schedule

    dispatch = {
        CB_MENU_SCHEDULE:  schedule.cmd_schedule,
        CB_MENU_UPCOMING:  schedule.cmd_upcoming,
        CB_MENU_PROFILE:   cmd_profile,
        # CB_MENU_USERS:     admin.cmd_users,
        # CB_MENU_ALL_EVENTS: admin.cmd_all_events,
    }

    handler = dispatch.get(query.data)
    if handler:
        await handler(update, context)


def _role_label(role: UserRole) -> str:
    return {
        UserRole.USER: "👤 Посетитель",
        UserRole.TRUSTED: "⭐ Доверенный",
        UserRole.HOST: "🎲 Организатор",
        UserRole.ADMIN: "⚔️ Администратор",
        UserRole.OWNER: "🔧 Разработчик",
    }.get(role, role.value)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = escape_user(await db.get_or_create_user(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        tg_username=tg_user.username,
    ))

    await update.message.reply_text(
        f"<b>Привет, {user.display_name}!</b>\n\n"
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
    
    user = escape_user(await db.get_or_create_user(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        tg_username=tg_user.username,
    ))

    member_since = (
        user.created_at.strftime("%d %b %Y")
        if user.created_at else "—"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✏️ Поменять имя", callback_data=CB_CHANGE_NAME)
    ]])

    await update.message.reply_text(
        f"<b>Ваш Профиль</b>\n\n"
        f"Отображаемое имя: <b>{user.display_name}</b>\n"
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

    if len(new_name) < MIN_NAME_LENGTH:
        await update.message.reply_text(f"Имя должно быть не меньше {MIN_NAME_LENGTH} символов. Введите имя еще раз:")
        return WAITING_FOR_NAME

    if len(new_name) > MAX_NAME_LENGTH:
        await update.message.reply_text(f"Имя должно быть не больше {MAX_NAME_LENGTH} символов. Введите имя еще раз:")
        return WAITING_FOR_NAME

    tg_user = update.effective_user
    current = await db.get_or_create_user(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        tg_username=tg_user.username,
    )
    user = escape_user(await db.update_display_name(current.id, new_name))
    await update.message.reply_text(
        f"Имя изменено на: <b>{user.display_name}</b>\n{COMMAND_END_MESSAGE_FOOTER}",
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

    # Menu button callbacks
    app.add_handler(CallbackQueryHandler(cb_menu_dispatch, pattern="^menu_"))
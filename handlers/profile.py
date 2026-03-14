from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
    # Every user sees these
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

    # Group into rows of 2
    rows = [all_buttons[i:i + 2] for i in range(0, len(all_buttons), 2)]
    return InlineKeyboardMarkup(rows)


def _role_label(role: UserRole) -> str:
    return {
        UserRole.USER: "👤 Посетитель",
        UserRole.TRUSTED: "👤 Trusted",
        UserRole.HOST: "🎪 Host",
        UserRole.ADMIN: "🛡 Admin",
        UserRole.OWNER: "👑 Owner",
    }.get(role, role.value)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user

    user, is_new = await db.get_or_create_user(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
    )

    if is_new:
        greeting = (
            f"☕ *Привет, {user.display_name}!*\n\n"
            f"Это УткоБот 🐸 (версия 0.1-альфа)\n"
            f"Ваша роль: {_role_label(user.role)}\n\n"
            f"Here's what you can do:"
        )
    else:
        greeting = (
            f"☕ *Снова привет, {user.display_name}!*\n\n"
            f"Role: {_role_label(user.role)}\n\n"
            f"Here's what you can do:"
        )

    await update.message.reply_text(
        greeting,
        parse_mode="Markdown",
        reply_markup=_build_menu(user.role),
    )


# ---------------------------------------------------------------------------
# /profile
# ---------------------------------------------------------------------------

async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user, _ = await db.get_or_create_user(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✏️ Change display name", callback_data=CB_CHANGE_NAME)
    ]])

    await update.message.reply_text(
        f"*Your Profile*\n\n"
        f"Display name: *{user.display_name}*\n"
        f"Role: {_role_label(user.role)}\n"
        f"Member since: {user.created_at.strftime('%d %b %Y') if user.created_at else '—'}",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# Change display name — inline button → ConversationHandler
# ---------------------------------------------------------------------------

async def cb_change_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "What would you like your display name to be?\n\n"
        "Send /cancel to keep your current name.",
    )
    return WAITING_FOR_NAME


async def received_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()

    if len(new_name) < 2:
        await update.message.reply_text("Name must be at least 2 characters. Try again:")
        return WAITING_FOR_NAME

    if len(new_name) > 64:
        await update.message.reply_text("Name must be 64 characters or fewer. Try again:")
        return WAITING_FOR_NAME

    user = await db.update_display_name(update.effective_user.id, new_name)
    await update.message.reply_text(
        f"✅ Display name updated to *{user.display_name}*.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_name_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Name change cancelled.")
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
"""
handlers/events.py
Handles all user-facing event interactions:
  /events  — browse upcoming events
  /myevents — events the user is signed up for
Inline button callbacks for sign-up / cancel / view detail.
"""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from handlers.utils import format_event_detail, format_event_summary, require_any_role
from models.models import User
from services import db

logger = logging.getLogger(__name__)

# Callback data prefixes — keep them short to stay within Telegram's 64-byte limit
CB_VIEW = "ev_view"
CB_SIGNUP = "ev_signup"
CB_CANCEL = "ev_cancel"
CB_BACK = "ev_back"


# ---------------------------------------------------------------------------
# /events command
# ---------------------------------------------------------------------------

@require_any_role
async def cmd_events(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    events = await db.list_upcoming_events()

    if not events:
        await update.message.reply_text("No upcoming events. Check back later! ☕")
        return

    await update.message.reply_text(
        "📅 *Upcoming events — tap one to see details:*",
        parse_mode="Markdown",
    )

    for event in events:
        signups = await db.list_signups_for_event(event.id)
        text = format_event_summary(event, signup_count=len(signups))
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📋 Details & Sign up", callback_data=f"{CB_VIEW}:{event.id}")]]
        )
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ---------------------------------------------------------------------------
# /myevents command
# ---------------------------------------------------------------------------

@require_any_role
async def cmd_my_events(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    signups = await db.list_signups_for_user(user.telegram_id)

    if not signups:
        await update.message.reply_text("You haven't signed up for any events yet.")
        return

    await update.message.reply_text("*Your upcoming events:*", parse_mode="Markdown")

    for signup in signups:
        event = await db.get_event(signup.event_id)
        if not event:
            continue
        all_signups = await db.list_signups_for_event(event.id)
        text = format_event_summary(event, signup_count=len(all_signups))
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel signup", callback_data=f"{CB_CANCEL}:{event.id}")]]
        )
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Inline button callbacks
# ---------------------------------------------------------------------------

async def cb_view_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    event_id = query.data.split(":")[1]
    tg_user = update.effective_user
    user = await db.get_or_create_user(tg_user.id, tg_user.username, tg_user.full_name)

    event = await db.get_event(event_id)
    if not event:
        await query.edit_message_text("Event not found.")
        return

    signups = await db.list_signups_for_event(event_id)
    is_signed_up = any(s.user_id == user.telegram_id for s in signups)
    is_full = len(signups) >= event.max_people

    text = format_event_detail(event, signups, user.telegram_id)

    buttons = []
    if is_signed_up:
        buttons.append(
            InlineKeyboardButton("❌ Cancel signup", callback_data=f"{CB_CANCEL}:{event_id}")
        )
    elif not is_full:
        buttons.append(
            InlineKeyboardButton("✅ Sign up", callback_data=f"{CB_SIGNUP}:{event_id}")
        )
    else:
        buttons.append(InlineKeyboardButton("🈵 Event full", callback_data="noop"))

    buttons.append(InlineKeyboardButton("⬅️ Back to list", callback_data=CB_BACK))

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([buttons]),
    )


async def cb_signup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    event_id = query.data.split(":")[1]
    tg_user = update.effective_user
    user = await db.get_or_create_user(tg_user.id, tg_user.username, tg_user.full_name)

    # Check not already signed up
    existing = await db.get_signup(event_id, user.telegram_id)
    if existing:
        await query.answer("You're already signed up!", show_alert=True)
        return

    success = await db.signup_for_event(event_id, user.telegram_id)
    if success:
        event = await db.get_event(event_id)
        await query.answer(f"✅ Signed up for {event.name}!", show_alert=True)
        # Refresh the message to reflect updated count
        signups = await db.list_signups_for_event(event_id)
        text = format_event_detail(event, signups, user.telegram_id)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel signup", callback_data=f"{CB_CANCEL}:{event_id}")]]
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await query.answer("Sorry, the event is full.", show_alert=True)


async def cb_cancel_signup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    event_id = query.data.split(":")[1]
    tg_user = update.effective_user
    user = await db.get_or_create_user(tg_user.id, tg_user.username, tg_user.full_name)

    await db.cancel_signup(event_id, user.telegram_id)

    event = await db.get_event(event_id)
    await query.answer(f"Signup cancelled for {event.name}.", show_alert=True)

    signups = await db.list_signups_for_event(event_id)
    text = format_event_detail(event, signups, user.telegram_id)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Sign up again", callback_data=f"{CB_SIGNUP}:{event_id}")]]
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Use /events to browse upcoming events.")


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

def register(app) -> None:
    app.add_handler(CommandHandler("events", cmd_events))
    app.add_handler(CommandHandler("myevents", cmd_my_events))
    app.add_handler(CallbackQueryHandler(cb_view_event, pattern=f"^{CB_VIEW}:"))
    app.add_handler(CallbackQueryHandler(cb_signup, pattern=f"^{CB_SIGNUP}:"))
    app.add_handler(CallbackQueryHandler(cb_cancel_signup, pattern=f"^{CB_CANCEL}:"))
    app.add_handler(CallbackQueryHandler(cb_back, pattern=f"^{CB_BACK}$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^noop$"))
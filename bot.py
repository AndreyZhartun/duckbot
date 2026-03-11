"""
bot.py
Wires all handlers together into a single Application instance.
Imported by app.py (the FastAPI server) which calls setup_application().
"""

from __future__ import annotations

import logging

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# from handlers import admin, events, host, templates

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# /start  and  /help — open to everyone
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    output: list[str] = [
        "Привет! Это УткоБот 🐸 (версия 0.1-альфа)\n",
        "Доступные команды:",
        "/help - показать это сообщение"
    ]

    reply = '\n'.join(output)

    # "☕ *Welcome to the Time Café bot!*\n\n"
    # "Here's what you can do:\n"
    # "/events — browse upcoming events\n"
    # "/myevents — events you're signed up for\n"
    # "/help — show this message\n\n"
    # "If you're a host:\n"
    # "/create\\_event — create a new event\n"
    # "/my\\_hosted — manage your hosted events\n"
    # "/create\\_template — set up a weekly recurring event\n"
    # "/my\\_templates — manage your templates"

    await update.message.reply_text(
        reply,
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def setup_application(token: str) -> Application:
    app = Application.builder().token(token).build()

    # General commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    # Domain handlers — each module registers its own handlers
    # events.register(app)
    # host.register(app)
    # templates.register(app)
    # admin.register(app)

    return app


async def set_bot_commands(app: Application) -> None:
    """
    Registers the command list that appears in Telegram's menu UI.
    Call this once after the bot is initialised.
    """
    commands = [
        BotCommand("start", "Welcome message & help"),
        BotCommand("help", "Show available commands"),
        # BotCommand("events", "Browse upcoming events"),
        # BotCommand("myevents", "Events you're signed up for"),
        # BotCommand("create_event", "Create a new event (hosts)"),
        # BotCommand("my_hosted", "Manage your hosted events (hosts)"),
        # BotCommand("create_template", "Create a weekly template (hosts)"),
        # BotCommand("my_templates", "Manage weekly templates (hosts)"),
        # BotCommand("users", "List all users (admin)"),
        # BotCommand("set_role", "Change a user's role (admin)"),
        # BotCommand("all_events", "See all events (admin)"),
        # BotCommand("cancel", "Cancel current multi-step flow"),
    ]
    await app.bot.set_my_commands(commands)
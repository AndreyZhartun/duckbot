from __future__ import annotations

import logging

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# from handlers import admin, events, host, templates
from handlers import profile, host, schedule
from services.database import close_engine
from constants import BOT_VERSION

logger = logging.getLogger(__name__)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    output: list[str] = [
        f"Привет! Это УткоБот 🐸 (версия {BOT_VERSION})",
        "Здесь позже будет полезная информация по боту"
    ]

    reply = '\n'.join(output)

    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def setup_application(token: str) -> Application:
    app = Application.builder().token(token).build()

    # General commands
    app.add_handler(CommandHandler("help", cmd_help))

    # Domain handlers — each module registers its own handlers
    # events.register(app)
    host.register(app)
    schedule.register(app)
    # templates.register(app)
    # admin.register(app)
    profile.register(app)

    return app


async def set_bot_commands(app: Application) -> None:
    """
    Registers the command list that appears in Telegram's menu UI.
    """
    commands = [
        BotCommand("start", "Главное меню"),
        BotCommand("profile", "Мой профиль"),
        BotCommand("help", "Помощь"),
        BotCommand("schedule", "This week's schedule"),
        BotCommand("upcoming", "Events after this week"),
        BotCommand("create_event", "Create a new event (hosts)"),
        BotCommand("users", "List all users (admin)"),
        BotCommand("set_role", "Change a user role (admin)"),
        BotCommand("all_events", "See all events (admin)"),
        BotCommand("cancel", "Cancel current multi-step flow"),
    ]
    await app.bot.set_my_commands(commands)
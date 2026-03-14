from __future__ import annotations

import logging

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# from handlers import admin, events, host, templates
from handlers import profile
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
        parse_mode="Markdown",
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
    # host.register(app)
    # templates.register(app)
    # admin.register(app)
    profile.register(app)

    return app


async def set_bot_commands(app: Application) -> None:
    """
    Registers the command list that appears in Telegram's menu UI.
    Call this once after the bot is initialised.
    """
    commands = [
        BotCommand("start", "Main menu"),
        BotCommand("profile", "View and edit your profile"),
        BotCommand("help", "Help"),
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
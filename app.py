from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application

from bot import set_bot_commands, setup_application
# from services.scheduler import start_scheduler

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

bot_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app

    token = os.environ["BOT_TOKEN"]
    webhook_url = os.environ["WEBHOOK_URL"]

    bot_app = setup_application(token)
    await bot_app.initialize()
    await bot_app.start()

    # Register Telegram command menu
    await set_bot_commands(bot_app)

    # Tell Telegram where to send updates
    await bot_app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message", "callback_query"],
    )
    logger.info(f"Webhook set to {webhook_url}")

    # Start weekly event scheduler
    # scheduler = start_scheduler()

    yield

    # --- shutdown ---
    # scheduler.shutdown(wait=False)
    await bot_app.bot.delete_webhook()
    await bot_app.stop()
    await bot_app.shutdown()
    logger.info("Bot shut down cleanly.")


app = FastAPI(lifespan=lifespan)

# /webhook endpoint for Telegram to POST updates to
@app.post("/webhook")
async def webhook(request: Request) -> Response:
    if bot_app is None:
        return Response(status_code=503)

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "bot_running": bot_app is not None}
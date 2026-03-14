from __future__ import annotations

import logging
import os
import signal
import sys

from dotenv import load_dotenv

from bot import set_bot_commands, setup_application
# from services.scheduler import start_scheduler

load_dotenv()

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),          # visible in systemd logs
        logging.FileHandler("bot.log"),             # persistent log file
    ],
)

# Quiet down overly verbose libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------

def check_env() -> None:
    """Fail fast if required environment variables are missing."""
    required = ["BOT_TOKEN"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        logger.critical(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    check_env()

    token = os.environ["BOT_TOKEN"]
    logger.info("Starting DuckBot in polling mode...")

    app = setup_application(token)

    # Start the weekly event scheduler
    # scheduler = start_scheduler()

    # Register bot commands in Telegram menu on every startup
    # (run_polling is synchronous so we use post_init for async setup)
    async def post_init(application) -> None:
        await set_bot_commands(application)
        logger.info("Bot commands registered.")

    app.post_init = post_init

    # Graceful shutdown on SIGTERM (sent by systemd on stop/restart)
    def handle_sigterm(*_) -> None:
        logger.info("SIGTERM received, shutting down...")
        # scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    logger.info("Bot is running. Press Ctrl+C to stop.")

    try:
        app.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,   # ignore messages sent while bot was offline
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested.")
    finally:
        # scheduler.shutdown(wait=False)
        logger.info("Bot stopped cleanly.")


if __name__ == "__main__":
    main()
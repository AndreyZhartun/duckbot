from html import escape
from models.models import User

# ---------------------------------------------------------------------------
# HTML escaping
# ---------------------------------------------------------------------------
 
def escape_user(user: User) -> User:
    """
    Returns a copy of the User with all string fields HTML-escaped.
    Use this before inserting any user data into HTML-parsed messages
    to prevent injection via display names or usernames.
 
    Usage:
        safe = escape_user(user)
        await update.message.reply_text(
            f"Hello, <b>{safe.display_name}</b>",
            parse_mode=ParseMode.HTML,
        )
    """
    from dataclasses import replace
    return replace(
        user,
        display_name=escape(user.display_name),
        tg_username=escape(user.tg_username) if user.tg_username else None,
    )
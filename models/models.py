from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    # standard user, can signup
    USER = "user"
    # (unused for now) maybe will be able to call untested commands
    TRUSTED = "trusted"
    # can host events
    HOST = "host"
    # can make hosts
    ADMIN = "admin"
    # can make admins
    OWNER = "owner"

@dataclass
class User:
    telegram_id: int
    # users can be added by username
    tg_username: Optional[str] = None
    # bot-specific name, editable by user
    # stays the same even if the user changes telegram name
    display_name: str
    role: UserRole
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


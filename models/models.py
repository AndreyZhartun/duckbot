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


class RoomChoice(str, Enum):
    ROOM_A = "room_a"
    ROOM_B = "room_b"
    BOTH   = "both"


@dataclass
class User:
    id:           str            # internal UUID — stable forever
    display_name: str            # bot-specific, editable by the user
    role:         UserRole
    telegram_id:  Optional[int]  = None  # None until user starts the bot
    tg_username:  Optional[str]  = None  # None if user has no TG username
    created_at:   Optional[datetime] = None
    updated_at:   Optional[datetime] = None


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------
 
@dataclass
class Event:
    id:                 str
    name:               str
    description:        str
    host_id:            str       # references User.id (internal UUID)
    room:               RoomChoice
    start_time:         datetime
    end_time:           datetime
    is_weekly_instance: bool          = False
    template_id:        Optional[str] = None


# ---------------------------------------------------------------------------
# Room  (static reference data — just two rows in the DB)
# ---------------------------------------------------------------------------

@dataclass
class Room:
    id:   str   # 'room_a' | 'room_b'
    name: str
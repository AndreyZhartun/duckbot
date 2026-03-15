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
    telegram_id: int
    # bot-specific name, editable by user
    # stays the same even if the user changes telegram name
    display_name: str
    role: UserRole
    # users can be added by username
    tg_username: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Event
#
# Future fields to add when implemented:
#   co_host_ids:  list[int]       — users with full edit/delete rights
#   signup_count: int             — denormalised counter for display
#   min_people:   int             — minimum to run the event
#   max_people:   int             — signup cap
# ---------------------------------------------------------------------------
 
@dataclass
class Event:
    id:                 str
    name:               str
    description:        str
    host_id:            int
    room:               RoomChoice
    start_time:         datetime
    end_time:           datetime
    is_weekly_instance: bool         = False
    template_id:        Optional[str] = None  # set when created from a template


# ---------------------------------------------------------------------------
# Room  (static reference data — just two rows in the DB)
# ---------------------------------------------------------------------------

@dataclass
class Room:
    id:   str   # 'room_a' | 'room_b'
    name: str
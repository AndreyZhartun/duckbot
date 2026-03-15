-- =============================================================================
-- Duck Bot — Database Initialisation
-- =============================================================================
-- ---------------------------------------------------------------------------
-- Shared trigger function — updates updated_at on every row change.
-- Created once here, reused by all tables that need it.
-- Must be created as superuser if botuser lacks CREATE FUNCTION permission.
-- ---------------------------------------------------------------------------
 
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
 
 
-- ---------------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------------
 
CREATE TABLE IF NOT EXISTS users (
    telegram_id     BIGINT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    tg_username     TEXT UNIQUE,
    role            TEXT NOT NULL DEFAULT 'user'
                        CONSTRAINT users_role_check
                        CHECK (role IN ('user', 'trusted', 'host', 'admin', 'owner')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
 
CREATE OR REPLACE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ---------------------------------------------------------------------------
-- Rooms  (static — just two rows)
-- ---------------------------------------------------------------------------
 
CREATE TABLE IF NOT EXISTS rooms (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
 
INSERT INTO rooms (id, name) VALUES
    ('room_a', 'Room A'),
    ('room_b', 'Room B')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Events
-- ---------------------------------------------------------------------------
 
CREATE TABLE IF NOT EXISTS events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    host_id             BIGINT NOT NULL REFERENCES users(telegram_id),
    room                TEXT NOT NULL
                            CONSTRAINT events_room_check
                            CHECK (room IN ('room_a', 'room_b', 'both')),
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ NOT NULL,
    is_weekly_instance  BOOLEAN NOT NULL DEFAULT false,
    -- template_id         UUID REFERENCES event_templates(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
 
    CONSTRAINT events_time_check CHECK (end_time > start_time)
);
 
CREATE OR REPLACE TRIGGER events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
 
CREATE INDEX IF NOT EXISTS events_start_time_idx  ON events (start_time);
CREATE INDEX IF NOT EXISTS events_host_idx        ON events (host_id);
CREATE INDEX IF NOT EXISTS events_room_time_idx   ON events (room, start_time, end_time);

-- ---------------------------------------------------------------------------
-- Permissions
-- Grants botuser access to all current and future tables in the schema.
-- ---------------------------------------------------------------------------
 
GRANT USAGE  ON SCHEMA public TO botuser;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO botuser;
GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO botuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO botuser;
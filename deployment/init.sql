-- =============================================================================
-- Duck Bot — Database Initialisation
-- =============================================================================
-- ---------------------------------------------------------------------------
-- Shared trigger — updates updated_at on every row change
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
--
-- id          — internal stable UUID, used everywhere as the FK target
-- telegram_id — optional until the user starts the bot
-- tg_username — optional (some accounts have none)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT        NOT NULL,
    role         TEXT        NOT NULL DEFAULT 'user'
                                 CONSTRAINT users_role_check
                                 CHECK (role IN ('user','trusted','host','admin','owner')),
    telegram_id  BIGINT      UNIQUE,          -- nullable
    tg_username  TEXT        UNIQUE,          -- nullable
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();


-- ---------------------------------------------------------------------------
-- Rooms  (static reference data)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS rooms (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

INSERT INTO rooms (id, name) VALUES
    ('room_a', 'Комната 1'),
    ('room_b', 'Комната 2')
ON CONFLICT DO NOTHING;


-- ---------------------------------------------------------------------------
-- Event templates  (weekly recurring — reserved for future use)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS event_templates (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name           TEXT        NOT NULL,
    description    TEXT        NOT NULL DEFAULT '',
    host_id        UUID        NOT NULL REFERENCES users(id),
    room           TEXT        NOT NULL
                                   CONSTRAINT templates_room_check
                                   CHECK (room IN ('room_a','room_b','both')),
    weekday        SMALLINT    NOT NULL CONSTRAINT templates_weekday_check CHECK (weekday BETWEEN 0 AND 6),
    start_hour     SMALLINT    NOT NULL CONSTRAINT templates_hour_check    CHECK (start_hour BETWEEN 0 AND 23),
    start_minute   SMALLINT    NOT NULL DEFAULT 0
                                   CONSTRAINT templates_minute_check CHECK (start_minute BETWEEN 0 AND 59),
    duration_hours NUMERIC(4,1) NOT NULL CONSTRAINT templates_duration_check CHECK (duration_hours BETWEEN 0.5 AND 12),
    is_active      BOOLEAN     NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE TRIGGER event_templates_updated_at
    BEFORE UPDATE ON event_templates
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();


-- ---------------------------------------------------------------------------
-- Events
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS events (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name               TEXT        NOT NULL,
    description        TEXT        NOT NULL DEFAULT '',
    host_id            UUID        NOT NULL REFERENCES users(id),
    room               TEXT        NOT NULL
                                       CONSTRAINT events_room_check
                                       CHECK (room IN ('room_a','room_b','both')),
    start_time         TIMESTAMPTZ NOT NULL,
    end_time           TIMESTAMPTZ NOT NULL,
    is_weekly_instance BOOLEAN     NOT NULL DEFAULT false,
    template_id        UUID        REFERENCES event_templates(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT events_time_check CHECK (end_time > start_time)
);

CREATE OR REPLACE TRIGGER events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE INDEX IF NOT EXISTS events_start_time_idx ON events (start_time);
CREATE INDEX IF NOT EXISTS events_host_idx        ON events (host_id);
CREATE INDEX IF NOT EXISTS events_room_time_idx   ON events (room, start_time, end_time);

-- ---------------------------------------------------------------------------
-- Permissions
-- ---------------------------------------------------------------------------

GRANT USAGE  ON SCHEMA public TO botuser;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO botuser;
GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO botuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO botuser;
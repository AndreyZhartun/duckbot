-- =============================================================================
-- Duck Bot — Database Initialisation
-- =============================================================================
-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
 
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid()
 
 
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
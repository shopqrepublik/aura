BEGIN;

CREATE TABLE IF NOT EXISTS product_events (
  event_id TEXT PRIMARY KEY,
  event_name TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id TEXT,
  anonymous_id TEXT,
  session_id TEXT,
  museum_id TEXT,
  artwork_id TEXT,
  recognition_attempt_id TEXT,
  properties JSONB,
  source TEXT,
  referrer TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  utm_content TEXT,
  country TEXT,
  city TEXT,
  language TEXT,
  device_type TEXT,
  os TEXT,
  browser TEXT,
  user_agent TEXT,
  path TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_events_name_time ON product_events (event_name, occurred_at);
CREATE INDEX IF NOT EXISTS idx_product_events_occurred_at ON product_events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_product_events_identity ON product_events (anonymous_id, user_id);
CREATE INDEX IF NOT EXISTS idx_product_events_session_id ON product_events (session_id);
CREATE INDEX IF NOT EXISTS idx_product_events_museum_id ON product_events (museum_id);
CREATE INDEX IF NOT EXISTS idx_product_events_artwork_id ON product_events (artwork_id);
CREATE INDEX IF NOT EXISTS idx_product_events_recognition_attempt_id ON product_events (recognition_attempt_id);

CREATE TABLE IF NOT EXISTS admin_sessions (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  last_seen_at TIMESTAMPTZ,
  ip_hash TEXT,
  user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_admin_sessions_token_hash ON admin_sessions (token_hash);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_expires_at ON admin_sessions (expires_at);

CREATE TABLE IF NOT EXISTS admin_login_attempts (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  ip_hash TEXT,
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  success BOOLEAN NOT NULL DEFAULT false,
  user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_email_time ON admin_login_attempts (email, attempted_at);
CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_ip_time ON admin_login_attempts (ip_hash, attempted_at);

COMMIT;
